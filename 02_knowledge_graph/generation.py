"""Generation — the 'G' in RAG — for the ISO 42001 Compliance Assistant.

Per-system remediation. Given ONE AI system and the specific ISO 42001 controls it
currently VIOLATES (judged from its own inventory record), the LLM writes owner-facing
guidance: for each violation, why the system is non-compliant with the organisation's
established policy, how to fix it, and exactly what to record back in the inventory to
clear the flag. Because violations differ per system, so does the output.

Backend is pluggable via LLM_BACKEND: template (default, no LLM, 0 tokens), ollama,
openai (any OpenAI-compatible server incl. the HF router / local vLLM), transformers.
Falls back to the template if the chosen backend is unavailable.
"""
import os
import re

SYSTEM_PROMPT = (
    "You are an ISO/IEC 42001 compliance assistant helping the business owner and "
    "technical owner of ONE AI system bring it into compliance with the organisation's "
    "existing, approved policies and procedures. Assume the policy set is complete; your "
    "job is not to critique policies but to help this system meet them. Use ONLY the "
    "violations and requirements provided. Do not invent controls or evidence. For each "
    "violation, address the owners directly: state what is non-compliant, how to remediate "
    "it, and exactly what to record in the AI system inventory to clear the flag. Be "
    "concrete and concise. Data is synthetic (fictional 'Meridian Financial Services')."
)


def approx_tokens(text):
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return max(1, len(text) // 4)


def build_prompt(system, violations):
    L = []
    L.append(f"AI SYSTEM: {system['id']} — {system['name']}")
    L.append(f"Purpose: {system['purpose']}")
    L.append(f"Business owner: {system.get('business_owner','?')} | "
             f"Technical owner: {system.get('technical_owner','?')}")
    L.append(f"Attributes: automated_decision={system['automated']}, "
             f"personal_data={system['personal_data']}, risk={system['risk']}")
    L.append("")
    if not violations:
        L.append("This system currently VIOLATES no applicable controls.")
    else:
        L.append(f"CONTROL VIOLATIONS FOR THIS SYSTEM ({len(violations)}):")
        L.append("(control | title | current state | requirement | governing procedure)")
        for v in violations:
            L.append(f"  {v['control']} | {v['title']} | current: {v['current']} | "
                     f"requirement: {v['requirement']} | procedure: {v.get('policy_ref') or '-'}")
    L.append("")
    L.append("TASK: Write remediation guidance addressed to the business and technical "
             "owners. Start with a one-sentence status line. Then, for EACH violation: "
             "(a) what is non-compliant and why it matters, (b) the concrete steps to "
             "remediate, (c) exactly which inventory field(s) to update and to what value "
             "once done. Reference the governing procedure where given. If there are no "
             "violations, confirm the system is compliant and say what to keep monitoring.")
    return SYSTEM_PROMPT, "\n".join(L)


def _gen_template(system, violations):
    o = []
    o.append(f"## Remediation plan — {system['id']} {system['name']}")
    o.append(f"*For: {system.get('business_owner','owner')} (business), "
             f"{system.get('technical_owner','owner')} (technical)*\n")
    if not violations:
        o.append(f"**Status.** {system['name']} meets all applicable ISO 42001 "
                 f"system-level controls in its current inventory record. Keep the review "
                 f"date, data-quality regime, and lineage current to stay compliant.")
        return "\n".join(o)
    o.append(f"**Status.** {system['name']} is non-compliant on {len(violations)} "
             f"applicable control(s). Actions below.\n")
    for i, v in enumerate(violations, 1):
        o.append(f"**{i}. {v['control']} - {v['title']}**")
        o.append(f"- Non-compliant: {v['current']}.")
        o.append(f"- Remediate: {v['requirement']}"
                 + (f" (per {v['policy_ref']})." if v.get('policy_ref') else "."))
        o.append(f"- Then update the inventory field for '{v['title'].lower()}' "
                 f"to its compliant value and re-submit.\n")
    return "\n".join(o)


def _chat_ollama(sys_p, usr_p):
    import requests
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.1")
    r = requests.post(f"{base}/api/chat", timeout=600, json={
        "model": model, "stream": False,
        "messages": [{"role": "system", "content": sys_p},
                     {"role": "user", "content": usr_p}]})
    r.raise_for_status()
    d = r.json()
    return (d["message"]["content"], model,
            {"prompt_tokens": d.get("prompt_eval_count"),
             "completion_tokens": d.get("eval_count")})


def _chat_openai(sys_p, usr_p):
    import requests
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    r = requests.post(f"{base}/chat/completions", headers=headers, timeout=600, json={
        "model": model, "temperature": 0.2,
        "messages": [{"role": "system", "content": sys_p},
                     {"role": "user", "content": usr_p}]})
    r.raise_for_status()
    d = r.json()
    u = d.get("usage", {})
    return (d["choices"][0]["message"]["content"], model,
            {"prompt_tokens": u.get("prompt_tokens"),
             "completion_tokens": u.get("completion_tokens")})


def _chat_transformers(sys_p, usr_p):
    from transformers import pipeline
    model = os.getenv("LLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
    pipe = pipeline("text-generation", model=model, device_map="auto")
    out = pipe([{"role": "system", "content": sys_p},
                {"role": "user", "content": usr_p}],
               max_new_tokens=800, do_sample=False)
    gen = out[0]["generated_text"]
    return (gen[-1]["content"] if isinstance(gen, list) else gen), model, {}


def draft_remediation(system, violations, backend=None):
    backend = (backend or os.getenv("LLM_BACKEND", "template")).lower()
    sys_p, usr_p = build_prompt(system, violations)
    est = approx_tokens(sys_p + "\n" + usr_p)
    res = {"backend": backend, "model": None, "prompt_tokens": est,
           "completion_tokens": None, "prompt": usr_p, "system_prompt": sys_p}
    try:
        if backend == "template":
            res["report"] = _gen_template(system, violations)
            res["model"] = "(deterministic template - no LLM, 0 generation tokens)"
            res["prompt_tokens"] = 0
        elif backend == "ollama":
            text, model, u = _chat_ollama(sys_p, usr_p)
            res.update(report=text, model=model,
                       prompt_tokens=u.get("prompt_tokens") or est,
                       completion_tokens=u.get("completion_tokens"))
        elif backend == "openai":
            text, model, u = _chat_openai(sys_p, usr_p)
            res.update(report=text, model=model,
                       prompt_tokens=u.get("prompt_tokens") or est,
                       completion_tokens=u.get("completion_tokens"))
        elif backend == "transformers":
            text, model, _ = _chat_transformers(sys_p, usr_p)
            res.update(report=text, model=model)
        else:
            res["report"] = _gen_template(system, violations)
            res["model"] = f"(unknown backend '{backend}' - used template)"
    except Exception as e:
        res["report"] = _gen_template(system, violations)
        res["model"] = f"(backend '{backend}' failed: {e} - fell back to template)"
        res["backend"] = f"{backend}->template"
    return res
