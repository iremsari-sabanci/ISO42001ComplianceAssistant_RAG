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
import retrieval

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


QA_SYSTEM_PROMPT = (
    "You are an ISO/IEC 42001 compliance assistant answering questions from the business "
    "or technical owner of ONE AI system. Answer ONLY from the retrieved context provided: "
    "the system's attributes and control statuses, and the extracts from the organisation's "
    "policy and procedure corpus. Cite the procedure document id (e.g. PR-SEC-002) when you "
    "rely on a policy extract, and the control id (e.g. A.7.4) when you rely on a control. "
    "Do not invent controls, evidence or procedures. If the retrieved context does not "
    "contain the answer, say so and suggest raising it with the AI Governance Team. Be "
    "concise and practical; when the owner asks how to fix something, give concrete steps "
    "and say which inventory field to update. Where a procedure extract is marked as a "
    "pending addition, make clear that the provision is not yet published and name the "
    "directorate responsible for publishing it."
)


def build_qa_context(system, controls, retrieved=None):
    """Assemble retrieved context: policy-corpus extracts + this system's control picture."""
    L = []
    if retrieved and retrieved.get("corpus"):
        L.append("RETRIEVED POLICY / PROCEDURE EXTRACTS (organisation's corpus):")
        for ch in retrieved["corpus"]:
            L.append(f"[{ch['doc_id']}] {ch['title']} - section: {ch['section']} "
                     f"(owner: {ch['owner']}; controls: {ch['controls']})")
            L.append(ch["text"][:1200])
            L.append("")
    if retrieved and retrieved.get("inherited"):
        L.append("INHERITED CONTROLS (added by knowledge-graph traversal):")
        for c in retrieved["inherited"]:
            L.append(f"  {c['control']} | {c['title']} | inherited from "
                     f"{c.get('_inherited_from','')}")
        L.append("")
    L += [f"AI SYSTEM: {system['id']} - {system['name']}",
         f"Purpose: {system['purpose']}",
         f"Business owner: {system.get('business_owner','?')} | "
         f"Technical owner: {system.get('technical_owner','?')}",
         f"Attributes: automated_decision={system['automated']}, "
         f"personal_data={system['personal_data']}, risk={system['risk']}", ""]
    L.append("CONTROL STATUS FOR THIS SYSTEM (control | title | status | current | procedure):")
    for c in controls:
        L.append(f"  {c['control']} | {c['title']} | {c['status']} | {c['current']} | "
                 f"{c.get('policy_ref') or '-'}")
    L.append("")
    L.append("CONTROL INTENT (what each control requires):")
    for c in controls:
        if c.get("requirement"):
            L.append(f"  {c['control']}: {c['requirement']}")
    return "\n".join(L)


def _qa_template(question, controls, retrieved=None):
    """Deterministic fallback: retrieve controls matching the question, no LLM."""
    q = (question or "").lower()
    hits = [c for c in controls
            if c["control"].lower() in q
            or any(w in q for w in c["title"].lower().split() if len(w) > 4)]
    if not hits and any(w in q for w in ("violation", "fix", "gap", "non-compliant",
                                        "remediat", "what should", "todo", "action")):
        hits = [c for c in controls if c["status"] == "Violation"]
    if not hits and not (retrieved or {}).get("corpus"):
        return ("Nothing in this system's control set or the policy corpus matches your question, so I can't "
                "answer it from the evidence available here. For questions beyond this "
                "system's ISO 42001 controls, ask the AI Governance Team.\n\n"
                "*(retrieval-only answer - no LLM backend configured)*")
    o = ["*(retrieval-only answer - no LLM backend configured)*", ""]
    for ch in (retrieved or {}).get("corpus", [])[:3]:
        o.append(f"**{ch['doc_id']} — {ch['title']}** · {ch['section']}")
        o.append(f"<small>owner: {ch['owner']}</small>")
        o.append(ch["text"][:500].replace("\n", " ") + " ...")
        o.append("")
    for c in hits[:5]:
        o.append(f"**{c['control']} - {c['title']}** ({c['status']})")
        o.append(f"- Current: {c['current']}")
        if c.get("requirement"):
            o.append(f"- Requires: {c['requirement']}")
        if c.get("policy_ref"):
            o.append(f"- Governing procedure: {c['policy_ref']}")
        o.append("")
    return "\n".join(o)


def answer_question(system, controls, question, history=None, backend=None, graph=None):
    """Grounded Q&A over one system's compliance picture. Returns the same shape as
    draft_remediation."""
    backend = (backend or os.getenv("LLM_BACKEND", "template")).lower()
    try:
        retrieved = retrieval.retrieve(question, controls=controls, g=graph)
    except Exception:
        retrieved = {"corpus": [], "controls": [], "inherited": []}
    ctx = build_qa_context(system, controls, retrieved)
    convo = ""
    for turn in (history or [])[-6:]:
        convo += f"\n{turn['role'].upper()}: {turn['content']}"
    usr = f"{ctx}\n\nCONVERSATION SO FAR:{convo or ' (none)'}\n\nQUESTION: {question}"
    est = approx_tokens(QA_SYSTEM_PROMPT + usr)
    res = {"backend": backend, "model": None, "prompt_tokens": est,
           "completion_tokens": None, "prompt": usr, "system_prompt": QA_SYSTEM_PROMPT,
           "retrieved": retrieved}
    try:
        if backend == "template":
            res.update(report=_qa_template(question, controls, retrieved),
                       model="(retrieval-only template - no LLM, 0 generation tokens)",
                       prompt_tokens=0)
        elif backend == "ollama":
            text, model, u = _chat_ollama(QA_SYSTEM_PROMPT, usr)
            res.update(report=text, model=model, prompt_tokens=u.get("prompt_tokens") or est,
                       completion_tokens=u.get("completion_tokens"))
        elif backend == "openai":
            text, model, u = _chat_openai(QA_SYSTEM_PROMPT, usr)
            res.update(report=text, model=model, prompt_tokens=u.get("prompt_tokens") or est,
                       completion_tokens=u.get("completion_tokens"))
        elif backend == "transformers":
            text, model, _ = _chat_transformers(QA_SYSTEM_PROMPT, usr)
            res.update(report=text, model=model)
        else:
            res.update(report=_qa_template(question, controls, retrieved),
                       model=f"(unknown backend '{backend}' - retrieval only)")
    except Exception as e:
        res.update(report=_qa_template(question, controls, retrieved),
                   model=f"(backend '{backend}' failed: {e} - retrieval only)",
                   backend=f"{backend}->template")
    return res


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
