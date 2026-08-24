"""ISO 42001 Compliance Assistant — role-based intake with adjudicated exemptions.

Roles: Business owner / Technical owner (own systems only) and AI Governance Team (all).
Owners answer the assistant's questions and may CLAIM a control is not applicable, with a
justification; the AI Governance Team approves or rejects the claim. Only Violations count
against a system; "Not answered" and "N/A pending" are tracked separately.

Run:  streamlit run compliance_app.py
Synthetic data - Meridian Financial Services (fictional).
"""
import os
import pandas as pd
import streamlit as st
from build_kg_networkx import load_graph
import core
import generation


def _apply_secrets():
    for k in ("LLM_BACKEND", "LLM_MODEL", "OPENAI_BASE_URL", "OPENAI_API_KEY",
              "OLLAMA_BASE_URL", "OLLAMA_MODEL"):
        try:
            if k in st.secrets:
                os.environ[k] = str(st.secrets[k])
        except Exception:
            pass


_apply_secrets()


@st.cache_resource
def get_graph():
    return load_graph()


@st.cache_data
def get_static():
    return core.load_inventory(), core.load_sysmap(), core.load_gov()


st.set_page_config(page_title="ISO 42001 Compliance Assistant", layout="wide")

try:
    g = get_graph()
    inv, sysmap, gov = get_static()
except FileNotFoundError as e:
    st.error(f"Could not load a data file: {e}")
    st.stop()

st.sidebar.header("Sign in")
role_label = st.sidebar.selectbox("Role", ["Business owner", "Technical owner",
                                           "AI Governance Team"])
ROLE = {"Business owner": "business", "Technical owner": "technical",
        "AI Governance Team": "governance"}[role_label]
if ROLE == "business":
    actor = st.sidebar.selectbox("You are", sorted(inv["Business_Owner"].unique()))
elif ROLE == "technical":
    actor = st.sidebar.selectbox("You are", sorted(inv["Technical_Owner"].unique()))
else:
    actor = "AI Governance Team"
st.sidebar.caption(f"Signed in as **{actor}** ({role_label}).")

my = core.systems_for_role(inv, ROLE, actor)
answers = core.load_answers()
exemptions = core.load_exemptions()

st.title("ISO 42001 Compliance Assistant")
st.caption("Synthetic data - Meridian Financial Services (fictional).")

if len(my) == 0:
    st.warning("No AI systems are assigned to you.")
    st.stop()

names = [f"{r.SYS_ID} - {r.System_Name}" for r in my.itertuples()]
pick = st.sidebar.selectbox("AI system", names)
row = my.iloc[names.index(pick)].to_dict()
role_filter = None if ROLE == "governance" else ROLE
controls = core.system_compliance(row, sysmap, gov, g, answers, exemptions, role=role_filter)
summ = core.summarise(controls)
viol = core.violations(controls)

tabs = ["Questions (intake)", "My compliance", "Risk & remediation (AI)"]
if ROLE == "governance":
    tabs += ["Exemption reviews", "Portfolio", "Governance readiness"]
T = st.tabs(tabs)

# ---------------- intake ----------------
with T[0]:
    st.subheader(f"{row['System_Name']} - questions for the {role_label.lower()}")
    if ROLE == "governance":
        st.info("Governance view: these are the questions asked of owners. Owners answer "
                "them in their own sign-in; governance adjudicates N/A claims.")
    else:
        st.caption("Answer these. If a control genuinely does not apply to this system, "
                   "claim 'Not applicable' with a justification - the AI Governance Team "
                   "reviews it. Claims do not count as compliant until approved.")
    for c in controls:
        if c["attribute"] == "__audit_current__" or not c["question"]:
            continue
        ex = c["exemption"]
        with st.container(border=True):
            st.markdown(f"**{c['question']}**  \n"
                        f"<small>{c['control']} · {c['title']} · status: "
                        f"<b>{c['status']}</b>"
                        + ("  ·  <i>answered by owner</i>" if c["owner_submitted"] else "")
                        + "</small>", unsafe_allow_html=True)
            if ex and ex.get("status") == "pending":
                st.warning(f"N/A claimed by {ex['claimed_by']} - awaiting AI Governance "
                           f"review.\n\n*Justification:* {ex['justification']}")
                if ROLE != "governance" and st.button("Withdraw claim",
                                                      key=f"wd_{row['SYS_ID']}_{c['control']}"):
                    core.withdraw_exemption(row["SYS_ID"], c["control"])
                    st.rerun()
                continue
            if ex and ex.get("status") == "approved":
                st.success(f"Not applicable - approved by {ex['reviewed_by']} "
                           f"({ex['reviewed_at'][:10]}).\n\n*Justification:* {ex['justification']}")
                continue
            if ex and ex.get("status") == "rejected":
                st.error(f"N/A claim rejected by {ex['reviewed_by']}."
                         + (f" Note: {ex['review_note']}" if ex.get("review_note") else "")
                         + " Please answer the question.")
            if not c.get("required", True):
                st.info(c.get("not_required_note")
                        or "ISO 42001 does not require a response for this system. "
                           "Answer only if applicable.")
            opts = c["options"] or ["Y", "N"]
            cur_val = c["value"] if c["value"] in opts else None
            idx = opts.index(cur_val) if cur_val else None
            choice = st.radio("Answer (optional)" if not c.get("required", True) else "Answer",
                              opts, index=idx, horizontal=True,
                              key=f"q_{row['SYS_ID']}_{c['attribute']}",
                              disabled=(ROLE == "governance"))
            if ROLE != "governance" and choice and choice != c["value"]:
                core.save_answer(row["SYS_ID"], c["attribute"], choice, ROLE, actor)
                st.rerun()
            if ROLE != "governance" and c["exemption_allowed"]:
                with st.expander("This control does not apply to my system"):
                    j = st.text_area("Justification (required)",
                                     key=f"j_{row['SYS_ID']}_{c['control']}",
                                     placeholder="e.g. this system produces no automated "
                                                 "decisions, so human oversight of automated "
                                                 "decisions does not apply.")
                    if st.button("Submit N/A claim for review",
                                 key=f"cl_{row['SYS_ID']}_{c['control']}"):
                        if not j.strip():
                            st.error("A justification is required.")
                        else:
                            core.claim_exemption(row["SYS_ID"], c["control"], j, ROLE, actor)
                            st.rerun()

# ---------------- compliance ----------------
with T[1]:
    st.subheader(row["System_Name"])
    st.write(row["System_Purpose"])
    c1 = st.columns(4)
    c1[0].markdown(f"**Automated decision**\n\n{row['Automated_Decision']}")
    c1[1].markdown(f"**Personal data**\n\n{row['Personal_Data']}")
    c1[2].markdown(f"**Risk level**\n\n{row['Risk_Level']}")
    c1[3].markdown(f"**Last review**\n\n{pd.to_datetime(row['Last_Audit_Date']).date()}")
    st.markdown(f"**Business owner:** {row['Business_Owner']}  ·  "
                f"**Technical owner:** {row['Technical_Owner']}")
    st.divider()
    if viol:
        st.error(f"{len(viol)} violation(s) require action.")
    elif summ["unanswered"] or summ["na_pending"]:
        st.warning("No violations, but intake is incomplete "
                   f"({summ['unanswered']} unanswered, {summ['na_pending']} N/A pending review).")
    else:
        st.success("Compliant on all applicable controls in this view.")
    m = st.columns(6)
    m[0].metric("Applicable", summ["applicable"])
    m[1].metric("Compliant", summ["compliant"])
    m[2].metric("Violations", summ["violations"])
    m[3].metric("Not answered", summ["unanswered"])
    m[4].metric("N/A pending", summ["na_pending"])
    m[5].metric("Not required", summ["not_required"])
    st.caption("Only violations count against the system. 'Not answered' is an intake gap; "
               "'N/A pending' awaits AI Governance review; approved N/A is excluded from scoring. "
               "'Not required' means the control is shown for transparency but ISO 42001 does not "
               "require a response for this system - the reason is explained in the intake tab.")
    st.dataframe(pd.DataFrame([{"control": x["control"], "title": x["title"],
                                "status": x["status"], "current state": x["current"],
                                "scope": x["scope"], "owner": x["owner_role"],
                                "governing procedure": x["policy_ref"]} for x in controls]),
                 use_container_width=True, hide_index=True)

# ---------------- remediation ----------------
with T[2]:
    sysd = {"id": row["SYS_ID"], "name": row["System_Name"], "purpose": row["System_Purpose"],
            "automated": row["Automated_Decision"], "personal_data": row["Personal_Data"],
            "risk": row["Risk_Level"], "business_owner": row["Business_Owner"],
            "technical_owner": row["Technical_Owner"]}
    backend = os.getenv("LLM_BACKEND", "template")
    st.caption(f"{row['System_Name']}: {len(viol)} violation(s), {summ['unanswered']} "
               f"unanswered. Backend: **{backend}**.")
    include_unanswered = st.checkbox("Also cover unanswered questions", value=True)
    items = list(viol) + (core.unanswered(controls) if include_unanswered else [])
    if st.button("Generate risk feedback & remediation"):
        with st.spinner("Generating..."):
            res = generation.draft_remediation(sysd, items, backend=backend)
        st.markdown(res["report"])
        st.divider()
        ct = res.get("completion_tokens")
        st.caption(f"backend: {res['backend']} · model: {res['model']} · "
                   f"prompt tokens ~ {res['prompt_tokens']} · "
                   f"completion tokens: {ct if ct is not None else 'n/a'}")
        with st.expander("Prompt sent to the LLM (input tokens)"):
            st.code(res["system_prompt"] + "\n\n" + res["prompt"])
        st.download_button("Download plan (.md)", res["report"],
                           file_name=f"remediation_{row['SYS_ID']}.md")

# ---------------- governance-only ----------------
if ROLE == "governance":
    with T[3]:
        st.subheader("Exemption reviews - AI Governance Team")
        st.caption("Owners claim a control is not applicable to their system; you decide. "
                   "Approved claims are excluded from that system's scoring and recorded "
                   "with the justification and approver (per-system Statement of "
                   "Applicability trail).")
        queue = core.pending_exemptions(inv, exemptions, sysmap)
        if not queue:
            st.info("No pending claims.")
        for q in queue:
            with st.container(border=True):
                st.markdown(f"**{q['sys_id']} {q['system']} — {q['control']} {q['title']}**  \n"
                            f"<small>claimed by {q['claimed_by']} ({q['claimed_role']}) on "
                            f"{q['claimed_at'][:16]}</small>", unsafe_allow_html=True)
                st.markdown(f"*Justification:* {q['justification']}")
                note = st.text_input("Review note (optional)",
                                     key=f"n_{q['sys_id']}_{q['control']}")
                a, b = st.columns(2)
                if a.button("Approve", key=f"ap_{q['sys_id']}_{q['control']}"):
                    core.review_exemption(q["sys_id"], q["control"], "approved", actor, note)
                    st.rerun()
                if b.button("Reject", key=f"rj_{q['sys_id']}_{q['control']}"):
                    core.review_exemption(q["sys_id"], q["control"], "rejected", actor, note)
                    st.rerun()

    with T[4]:
        st.subheader("Portfolio - AI Governance Team only")
        rows = []
        for r in inv.itertuples():
            rd = r._asdict()
            ctrls = core.system_compliance(rd, sysmap, gov, g, answers, exemptions)
            s = core.summarise(ctrls)
            rows.append({"SYS_ID": r.SYS_ID, "System": r.System_Name, "Risk": r.Risk_Level,
                         "Applicable": s["applicable"], "Compliant": s["compliant"],
                         "Violations": s["violations"], "Not answered": s["unanswered"],
                         "N/A pending": s["na_pending"], "N/A approved": s["na_approved"],
                         "Not required": s["not_required"],
                         "Status": "NON-COMPLIANT" if s["violations"] else
                                   ("INTAKE INCOMPLETE" if s["unanswered"] or s["na_pending"]
                                    else "COMPLIANT"),
                         "Business owner": r.Business_Owner,
                         "Technical owner": r.Technical_Owner})
        pdf = pd.DataFrame(rows).sort_values(["Violations", "Not answered"], ascending=False)
        st.dataframe(pdf, use_container_width=True, hide_index=True)
        st.caption("Exemption claims are visible here so a green score cannot be "
                   "manufactured by claiming N/A.")

    with T[5]:
        st.subheader("Governance readiness (org-level)")
        st.caption("Is our policy/procedure set itself complete against Annex A? Assessed "
                   "once org-wide - not per system.")
        gl = list(gov.values())
        m = st.columns(3)
        m[0].metric("Annex A controls", len(gl))
        m[1].metric("Policy evidence present",
                    len([r for r in gl if r["evidence_status"] == "evidence_present"]))
        m[2].metric("Policy gaps to close",
                    len([r for r in gl if r["evidence_status"] == "gap"]))
        st.dataframe(pd.DataFrame([{"control": r["control_id"], "title": r["title"],
                                    "policy status": r["evidence_status"],
                                    "evidence": r["evidence_source"]} for r in gl]),
                     use_container_width=True, hide_index=True)
        st.divider()
        st.markdown("**Per-system control scope & justification**")
        st.caption("Why each control is assessed per system (A.8.4 is organizational; its "
                   "per-system question asks only whether this system is covered).")
        st.dataframe(pd.DataFrame([{"control": r["control_id"], "title": r["title"],
                                    "scope": r.get("scope", ""),
                                    "N/A claim allowed": r.get("exemption_allowed", ""),
                                    "justification": r.get("per_system_justification", "")}
                                   for r in sysmap]),
                     use_container_width=True, hide_index=True)
