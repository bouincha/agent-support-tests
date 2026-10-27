"""Mock LLM compatible OpenAI (/v1/chat/completions), deterministe, avec appels d'outils (stream ou non).
Sert a tester le WORKFLOW (cablage, outils, logs, masquage, alertes) sans cle API ni cout, de facon reproductible.
Regles sur le dernier message client: CMD-xxxx -> outil commande | plainte/litige/probleme -> ticket | retour/livraison/garantie -> FAQ | sinon salutation.
Chaque requete recue est ajoutee a MOCK_LOG (une ligne JSON)."""
import json, os, re, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = os.environ.get("MOCK_LOG", "")

def pick(tools, key):
    for t in tools or []:
        if key in t["function"]["name"].lower():
            return t["function"]["name"]

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        b = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        ms, tools = b["messages"], b.get("tools")
        last = ms[-1]
        user = [m for m in ms if m["role"] == "user"][-1]["content"]
        if isinstance(user, list): user = " ".join(p.get("text", "") for p in user)
        if LOG:
            with open(LOG, "a", encoding="utf-8") as f: f.write(json.dumps({"user": user, "n_tools": len(tools or []), "last_role": last["role"]}, ensure_ascii=False) + "\n")
        cid = (re.search(r"\[(REQ-\w+)\]", user) or [None, ""])[1]
        if last["role"] == "tool":
            msg = {"role": "assistant", "content": "Resultat: " + str(last["content"])[:300]}
        else:
            call = None
            m = re.search(r"CMD-\d+", user)
            if m and pick(tools, "order"): call = (pick(tools, "order"), {"order_id": m.group(0)})
            elif re.search(r"plainte|litige|probl", user, re.I) and pick(tools, "ticket"): call = (pick(tools, "ticket"), {"summary": user[:300], "priority": "high", "correlation_id": cid})
            elif re.search(r"retour|livraison|garantie", user, re.I) and pick(tools, "faq"): call = (pick(tools, "faq"), {"query": user[:300]})
            msg = ({"role": "assistant", "content": None, "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": call[0], "arguments": json.dumps(call[1], ensure_ascii=False)}}]}
                   if call else {"role": "assistant", "content": "Bonjour ! Comment puis-je vous aider ?"})
        usage = {"prompt_tokens": 420, "completion_tokens": 90, "total_tokens": 510}
        if b.get("stream"):
            ch = lambda d, fin=None: "data: " + json.dumps({"id": "c", "object": "chat.completion.chunk", "model": b["model"], "choices": [{"index": 0, "delta": d, "finish_reason": fin}]}) + "\n\n"
            body = ch({"role": "assistant", "content": ""})
            if msg.get("tool_calls"):
                tc = msg["tool_calls"][0]; body += ch({"tool_calls": [{"index": 0, "id": tc["id"], "type": "function", "function": tc["function"]}]}) + ch({}, "tool_calls")
            else:
                body += ch({"content": msg["content"]}) + ch({}, "stop")
            body += "data: " + json.dumps({"id": "c", "object": "chat.completion.chunk", "model": b["model"], "choices": [], "usage": usage}) + "\n\ndata: [DONE]\n\n"
            out, ct = body.encode(), "text/event-stream"
        else:
            out = json.dumps({"id": "c", "object": "chat.completion", "model": b["model"], "choices": [{"index": 0, "message": msg, "finish_reason": "tool_calls" if msg.get("tool_calls") else "stop"}], "usage": usage}, ensure_ascii=False).encode()
            ct = "application/json"
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
