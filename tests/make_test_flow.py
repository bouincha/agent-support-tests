"""Transforme l'export Langflow en variante de test: l'Agent utilise le mock LLM (a la place du noeud OpenRouter)
et des reglages par cas (simulation de panne, seuils d'alerte...) sont appliques. Le flow lui-meme n'est pas modifie."""
import copy, importlib, inspect

_AGENT = None

def _agent_node():
    global _AGENT
    if _AGENT is None:
        from lfx.custom.utils import build_custom_component_template
        from lfx.custom.custom_component.component import Component
        mod = importlib.import_module("lfx.components.models_and_agents.agent")
        _AGENT, _ = build_custom_component_template(Component(_code=inspect.getsource(mod)))
    return copy.deepcopy(_AGENT)

def build_test_flow(flow, mock_url, api_key="sk-test-SECRET-KEY", overrides=None):
    f = copy.deepcopy(flow)
    nodes = f["data"]["nodes"]
    for n in nodes:
        if n["data"]["type"] == "Agent":
            node = _agent_node(); t = node["template"]
            t["agent_llm"]["value"] = "OpenAI"; t["model_name"]["value"] = "mock-model"; t["openai_api_base"]["value"] = mock_url
            t["api_key"]["value"] = api_key; t["max_iterations"]["value"] = 6; t["add_current_date_tool"]["value"] = False
            n["data"]["node"] = node
    drop = {n["id"] for n in nodes if n["data"]["type"].startswith("OpenRouter")}
    f["data"]["nodes"] = [n for n in nodes if n["id"] not in drop]
    f["data"]["edges"] = [e for e in f["data"]["edges"] if e["source"] not in drop and e["target"] not in drop]
    for prefix, fields in (overrides or {}).items():
        hit = [n for n in f["data"]["nodes"] if n["id"].startswith(prefix)]
        if not hit: raise KeyError("noeud introuvable pour l'override: " + prefix)
        for k, v in fields.items(): hit[0]["data"]["node"]["template"][k]["value"] = v
    return f
