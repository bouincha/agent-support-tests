#!/usr/bin/env python3
"""Runner + Scorer de la suite de tests de l'agent (low-code: les cas de test sont des donnees JSON).

  python tests/run_tests.py                   # suite deterministe avec mock LLM (CI)
  python tests/run_tests.py --live            # cas [LIVE] avec le vrai modele (OPENROUTER_API_KEY requis)
  python tests/run_tests.py --update-baseline # enregistre les resultats comme reference de non-regression

Chaque cas lance le flow Langflow en mode headless (`lfx run`) dans un dossier de logs isole (OBS_HOME), puis verifie des regles.
Sorties: reports/report.md, report.json, junit.xml. Code retour 1 si un test echoue ou s'il y a une regression."""
import argparse, csv, json, os, re, shutil, socket, subprocess, sys, tempfile, time, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_test_flow import build_test_flow

EXEC_COLS = ["correlation_id", "timestamp", "utilisateur", "statut", "duree_totale_ms", "tokens_in", "tokens_out", "cout_usd", "intent", "outil", "nb_etapes", "erreur", "question_masquee"]
TYPES = [("format", "Format (sorties)"), ("integration", "Intégration (enchaînements)"), ("policy", "Policy (règles)"), ("mauvaise_entree", "Mauvaise entrée (robustesse)")]

def read_csv(p):
    if not Path(p).exists(): return []
    with open(p, newline="", encoding="utf-8") as f: return list(csv.DictReader(f))

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def parse_reply(text):
    cid = (re.search(r"`(REQ-[A-F0-9]{6}|REQ-INCONNU)`", text) or [None, ""])[1]
    m = re.search(r"`REQ-[A-F0-9]{6}` · (\w+) · (\d+) ms · (\d+) étapes", text)
    steps = [(n, int(d), ok) for n, d, ok in re.findall(r"- [🔧🧠] `([^`]+)` (\d+) ms (✓|✗)", text)]
    tools = [n for n, _ in re.findall(r"- 🔧 `([^`]+)` (\d+) ms", text)]
    return {"cid": cid, "statut": m.group(1) if m else "", "steps": steps, "tools": tools, "n_steps": int(m.group(3)) if m else len(steps)}

def seed_files(home, seed):
    home.mkdir(parents=True, exist_ok=True)
    if seed and seed.get("executions"):
        with open(home / "executions.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=EXEC_COLS); w.writeheader()
            for r in seed["executions"]:
                row = {c: "" for c in EXEC_COLS}; row.update({"timestamp": datetime.now().isoformat(timespec="seconds"), "tokens_in": 100, "tokens_out": 20, "nb_etapes": 2}); row.update(r); w.writerow(row)

def evaluate(chk, ctx):
    t, reply, home = chk["type"], ctx["reply"], ctx["home"]
    info = parse_reply(reply); csvs = [p for p in Path(home).glob("*.csv")]
    allcsv = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in csvs)
    if t == "run_ok": return ctx["rc"] == 0 and bool(reply.strip()), "code retour %s, réponse %s" % (ctx["rc"], "vide" if not reply.strip() else "non vide")
    if t == "reply_contains": return chk["text"] in reply, "texte attendu: %r" % chk["text"]
    if t == "reply_not_contains": return chk["text"] not in reply, "texte interdit: %r" % chk["text"]
    if t == "reply_regex": return bool(re.search(chk["pattern"], reply)), "motif attendu: %s" % chk["pattern"]
    if t == "reply_not_regex": return not re.search(chk["pattern"], reply), "motif interdit: %s" % chk["pattern"]
    if t == "tools_called": return sorted(info["tools"]) == sorted(chk["tools"]), "outils appelés: %s (attendu %s)" % (info["tools"], chk["tools"])
    if t == "tools_none": return not info["tools"], "outils appelés: %s" % info["tools"]
    if t == "steps_count": return info["n_steps"] == chk["n"], "étapes: %s (attendu %s)" % (info["n_steps"], chk["n"])
    if t == "step_duration_gt":
        d = [ms for n, ms, _ in info["steps"] if chk["tool"] in n]; return bool(d) and max(d) > chk["ms"], "durées de %s: %s ms (min attendu %s)" % (chk["tool"], d, chk["ms"])
    if t == "csv_header":
        p = Path(home) / chk["file"]; head = p.read_text(encoding="utf-8").splitlines()[0].split(",") if p.exists() else []
        return head == chk["columns"], "colonnes: %s" % head
    if t == "csv_parseable":
        try: rows = read_csv(Path(home) / chk["file"]); return len(rows) > 0, "%d lignes lues" % len(rows)
        except Exception as e: return False, "illisible: %s" % e
    if t == "csv_contains": return chk["text"] in allcsv, "texte attendu dans les logs: %r" % chk["text"]
    if t == "csv_not_contains": return chk["text"] not in allcsv, "texte interdit dans les logs: %r" % chk["text"]
    if t == "exec_field":
        rows = read_csv(Path(home) / "executions.csv"); v = rows[-1].get(chk["field"], "") if rows else ""
        return (v == chk["equals"]) if "equals" in chk else (chk["contains"] in v), "%s = %r" % (chk["field"], v)
    if t == "exec_cid_matches_reply":
        rows = read_csv(Path(home) / "executions.csv"); return bool(rows) and rows[-1]["correlation_id"] == info["cid"] != "REQ-INCONNU", "reply=%s, csv=%s" % (info["cid"], rows[-1]["correlation_id"] if rows else None)
    if t == "ticket_linked":
        tk = read_csv(Path(home) / "tickets.csv"); return any(r["correlation_id"] == info["cid"] for r in tk) and info["cid"] != "", "reply=%s, tickets=%s" % (info["cid"], [r["correlation_id"] for r in tk])
    if t == "reply_has_prev_cids": return bool(ctx["prev_cids"]) and all(c in reply for c in ctx["prev_cids"]), "attendus: %s" % ctx["prev_cids"]
    if t == "mock_log_not_contains":
        log = Path(ctx["mock_log"]).read_text(encoding="utf-8") if ctx.get("mock_log") and Path(ctx["mock_log"]).exists() else ""
        return chk["text"] not in log, "le LLM a reçu un message contenant %r" % chk["text"]
    return False, "type de vérification inconnu: " + t

def run_case(case, flow, args, lfx, mock_url, mock_log):
    t0 = time.time(); home = Path(tempfile.mkdtemp(prefix="obs_" + case["id"] + "_"))
    seed_files(home / "logs", case.get("seed"))
    overrides = {"ObsStart": {"simulation": case.get("simulation", "aucune")}}
    for k, v in (case.get("overrides") or {}).items(): overrides.setdefault(k, {}).update(v)
    if args.live:
        f = json.loads(json.dumps(flow))
        for n in f["data"]["nodes"]:
            if n["data"]["type"].startswith("OpenRouter"):
                n["data"]["node"]["template"]["api_key"]["value"] = os.environ["OPENROUTER_API_KEY"]; n["data"]["node"]["template"]["model_name"]["value"] = os.environ.get("LIVE_MODEL", "openai/gpt-4o-mini")
        for p, fl in overrides.items():
            for n in f["data"]["nodes"]:
                if n["id"].startswith(p):
                    for k, v in fl.items(): n["data"]["node"]["template"][k]["value"] = v
    else:
        f = build_test_flow(flow, mock_url, overrides=overrides)
    fp = home / "flow.json"; fp.write_text(json.dumps(f, ensure_ascii=False), encoding="utf-8")
    env = dict(os.environ, OBS_HOME=str(home / "logs"), MOCK_LOG=mock_log or "", PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    replies, prev, rc = [], [], 0
    for i, msg in enumerate(case["messages"]):
        try:
            r = subprocess.run([lfx, "run", str(fp), msg, "--format", "text"], capture_output=True, encoding="utf-8", errors="replace", env=env, timeout=args.timeout)
            rc, out = r.returncode, r.stdout
        except subprocess.TimeoutExpired:
            rc, out = 124, ""
        replies.append(out)
        if i < len(case["messages"]) - 1:
            c = parse_reply(out)["cid"]
            if c: prev.append(c)
    ctx = {"reply": replies[-1], "rc": rc, "home": home / "logs", "prev_cids": prev, "mock_log": mock_log}
    results = []
    for chk in case["checks"]:
        try: ok, detail = evaluate(chk, ctx)
        except Exception as e: ok, detail = False, "erreur d'évaluation: %s" % e
        results.append({"check": chk["type"], "ok": bool(ok), "detail": detail})
    passed = all(r["ok"] for r in results)
    shutil.rmtree(home, ignore_errors=True)
    return {"id": case["id"], "type": case["type"], "title": case["title"], "passed": passed, "seconds": round(time.time() - t0, 1), "checks": results, "reply_excerpt": replies[-1][:300]}

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--flow", default=str(ROOT / "flows" / "Support_Client_Observable_patched.json")); ap.add_argument("--cases", default=str(ROOT / "tests" / "golden_cases.json"))
    ap.add_argument("--live", action="store_true"); ap.add_argument("--update-baseline", action="store_true"); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=240); ap.add_argument("--out", default=str(ROOT / "reports")); ap.add_argument("--only", default="")
    args = ap.parse_args(); lfx = os.environ.get("LFX_BIN", "lfx")
    flow = json.load(open(args.flow, encoding="utf-8")); cases = [c for c in json.load(open(args.cases, encoding="utf-8"))["cases"] if bool(c.get("live")) == args.live]
    if args.only: cases = [c for c in cases if c["id"] in args.only.split(",")]
    if args.live and "OPENROUTER_API_KEY" not in os.environ: sys.exit("OPENROUTER_API_KEY manquant pour --live")
    server = None; mock_url = mock_log = None; tmp = tempfile.mkdtemp(prefix="mock_")
    if not args.live:
        port = free_port(); mock_log = str(Path(tmp) / "mock.log"); mock_url = "http://127.0.0.1:%d/v1" % port
        server = subprocess.Popen([sys.executable, str(ROOT / "tests" / "mock_llm.py"), str(port)], env=dict(os.environ, MOCK_LOG=mock_log, PYTHONUTF8="1")); time.sleep(1.2)
    t0 = time.time()
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as ex: results = list(ex.map(lambda c: run_case(c, flow, args, lfx, mock_url, mock_log), cases))
    finally:
        if server: server.terminate()
    # --- baseline / non-regression
    bpath = ROOT / "tests" / ("baseline_live.json" if args.live else "baseline.json")
    base = json.load(open(bpath)) if bpath.exists() else {}
    regress = [r["id"] for r in results if base.get(r["id"]) == "pass" and not r["passed"]]
    if args.update_baseline: json.dump({r["id"]: "pass" if r["passed"] else "fail" for r in results}, open(bpath, "w"), indent=1)
    # --- rapports
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    n, ok = len(results), sum(r["passed"] for r in results); rate = 100.0 * ok / max(1, n)
    md = ["# Rapport de tests - Agent Support Client", "", "Date: %s | Mode: %s | Durée: %.0f s" % (datetime.now().strftime("%Y-%m-%d %H:%M"), "LIVE (vrai modèle)" if args.live else "mock LLM (déterministe)", time.time() - t0), "",
          "## Résultat global: %s - %d/%d cas réussis (%.0f %%)" % ("SUCCÈS" if ok == n and not regress else "ÉCHEC", ok, n, rate), "",
          "Non-régression: %s" % ("aucune régression par rapport à la référence" if not regress else "RÉGRESSIONS: " + ", ".join(regress)), "", "## Par type de test", "", "| Type | Réussis | Total |", "|---|---|---|"]
    for k, label in TYPES:
        rs = [r for r in results if r["type"] == k]
        if rs: md.append("| %s | %d | %d |" % (label, sum(r["passed"] for r in rs), len(rs)))
    md += ["", "## Détail des cas", "", "| ID | Type | Cas | Résultat | Durée |", "|---|---|---|---|---|"]
    for r in results: md.append("| %s | %s | %s | %s | %s s |" % (r["id"], r["type"], r["title"], "PASS" if r["passed"] else "**FAIL**", r["seconds"]))
    fails = [r for r in results if not r["passed"]]
    if fails:
        md += ["", "## Échecs", ""]
        for r in fails:
            md.append("### %s - %s" % (r["id"], r["title"]))
            md += ["- %s: %s" % (c["check"], c["detail"]) for c in r["checks"] if not c["ok"]]
            md.append("- Extrait de la réponse: `%s`" % r["reply_excerpt"].replace("\n", " ")[:200])
    (out / ("report_live.md" if args.live else "report.md")).write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / ("report_live.json" if args.live else "report.json")).write_text(json.dumps({"passed": ok, "total": n, "rate": rate, "regressions": regress, "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    ts = ET.Element("testsuite", name="agent-support", tests=str(n), failures=str(n - ok))
    for r in results:
        tc = ET.SubElement(ts, "testcase", classname=r["type"], name="%s %s" % (r["id"], r["title"]), time=str(r["seconds"]))
        if not r["passed"]: ET.SubElement(tc, "failure", message="; ".join(c["detail"] for c in r["checks"] if not c["ok"]))
    ET.ElementTree(ts).write(out / "junit.xml", encoding="utf-8", xml_declaration=True)
    print("\n".join(md[:8 + len(TYPES) + 3]))
    sys.exit(0 if ok == n and not regress else 1)

if __name__ == "__main__":
    main()
