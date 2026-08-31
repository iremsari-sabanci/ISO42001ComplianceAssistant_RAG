"""ISO 42001 Compliance Assistant — role-based intake with adjudicated exemptions.

Roles: Business owner / Technical owner (own systems only) and AI Governance Team (all).
Owners answer the assistant's questions and may CLAIM a control is not applicable, with a
justification; the AI Governance Team approves or rejects the claim. Only Violations count
against a system; "Not answered" and "N/A pending" are tracked separately.

Run:  streamlit run compliance_app.py
Synthetic data - Meridian Financial Services (fictional).
"""
import os
import datetime as dt
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
    return (core.load_inventory(), core.load_sysmap(), core.load_gov(),
            core.load_procmap())


st.set_page_config(page_title="ISO 42001 Compliance Assistant", layout="wide")

try:
    g = get_graph()
    inv, sysmap, gov, procmap = get_static()
except FileNotFoundError as e:
    st.error(f"Could not load a data file: {e}")
    st.stop()

st.sidebar.header("Sign in")
role_label = st.sidebar.selectbox("Role", ["Business owner", "Technical owner",
                                           "AI Governance Team",
                                           "Procedure owner (policy/procedure)"])
ROLE = {"Business owner": "business", "Technical owner": "technical",
        "AI Governance Team": "governance",
        "Procedure owner (policy/procedure)": "procedure"}[role_label]
if ROLE == "business":
    actor = st.sidebar.selectbox("You are", sorted(inv["Business_Owner"].unique()))
elif ROLE == "technical":
    actor = st.sidebar.selectbox("You are", sorted(inv["Technical_Owner"].unique()))
elif ROLE == "procedure":
    actor = st.sidebar.selectbox("Your department", core.PROCEDURE_OWNERS)
else:
    actor = "AI Governance Team"
st.sidebar.caption(f"Signed in as **{actor}** ({role_label}).")

if ROLE == "procedure":
    st.title("ISO 42001 Compliance Assistant")
    st.subheader(f"Policy & procedure actions — {actor}")
    st.caption("Annex A controls where the AI Governance Team has identified a policy or "
               "procedure gap and assigned it to your department. Record what you are "
               "doing and the resulting document reference.")
    actions = core.load_policy_actions()
    mine = [r for r in core.governance_readiness(gov, actions, procmap)
            if r["assigned_to"] == actor]
    reqs = core.proc_requests_for(actor)

    if reqs:
        st.markdown("### Procedure update requests from the AI Governance Team")
        st.caption("Additions the AI Governance Team has asked your department to make. "
                   "Your department drafts, approves and publishes them; the AI Governance "
                   "Team tracks closure but does not author your procedures.")
        for r in reqs:
            with st.container(border=True):
                st.markdown(f"**{r['id']} — {r['procedure']}**"
                            + (f"  ·  section: {r['section']}" if r["section"] else "")
                            + f"  \n<small>control: {r['control'] or '-'} · due: "
                              f"{r['due_date'] or '-'} · status: <b>{r['status']}</b></small>",
                            unsafe_allow_html=True)
                st.markdown(r["addition"])
                s_ = st.selectbox("Status", core.PROC_REQUEST_STATUS,
                                  index=core.PROC_REQUEST_STATUS.index(r["status"])
                                  if r["status"] in core.PROC_REQUEST_STATUS else 0,
                                  key=f"prs_{r['id']}")
                resp = st.text_area("Your response (what was added, or why not)",
                                    value=r["owner_response"], key=f"prr_{r['id']}")
                if st.button("Save response", key=f"prb_{r['id']}"):
                    core.respond_proc_request(r["id"], s_, resp, actor)
                    st.rerun()
        st.divider()

    if not mine:
        if not reqs:
            st.info("No policy actions or procedure update requests are assigned to your "
                    "department.")
        st.stop()
    st.markdown("### Annex A policy gaps assigned to your department")
    open_n = len([r for r in mine if r["action_status"] != "Completed"])
    m = st.columns(2)
    m[0].metric("Assigned to you", len(mine))
    m[1].metric("Still open", open_n)
    for r in mine:
        with st.container(border=True):
            st.markdown(f"**{r['control_id']} — {r['title']}**  \n"
                        f"<small>policy status: {r['policy_status']} · due: "
                        f"{r['due_date'] or '—'} · assigned by AI Governance</small>",
                        unsafe_allow_html=True)
            if r.get("proposed_procedure"):
                st.caption(f"Proposed procedure: **{r['proposed_procedure']}** "
                           f"({r.get('new_or_addition','')})")
            if r["governance_note"]:
                st.info(f"Governance note: {r['governance_note']}")
            s = st.selectbox("Status", core.POLICY_ACTION_STATUS,
                             index=core.POLICY_ACTION_STATUS.index(r["action_status"])
                             if r["action_status"] in core.POLICY_ACTION_STATUS else 0,
                             key=f"ps_{r['control_id']}")
            upd = st.text_area("What you are doing / what was added",
                               value=r["owner_update"], key=f"pu_{r['control_id']}")
            ev = st.text_input("Resulting document reference (e.g. PR-SEC-003 §4)",
                               value=r["evidence_ref"], key=f"pe_{r['control_id']}")
            if st.button("Save update", key=f"pb_{r['control_id']}"):
                core.update_policy_action(r["control_id"], s, upd, ev, actor)
                st.success("Recorded.")
                st.rerun()
    st.stop()

my = core.systems_for_role(inv, ROLE, actor)
answers = core.load_answers()
exemptions = core.load_exemptions()
intended_use = core.load_intended_use()
reviews = core.load_reviews()

st.title("ISO 42001 Compliance Assistant")
st.caption("Data sources: an AI system inventory adapted and de-identified from an "
           "institutional inventory, and ISO/IEC 42001:2023 Annex A. See DATA_SOURCES.md.")

if len(my) == 0:
    st.warning("No AI systems are assigned to you.")
    st.stop()

names = [f"{r.SYS_ID} - {r.System_Name}" for r in my.itertuples()]
pick = st.sidebar.selectbox("AI system", names)
row = my.iloc[names.index(pick)].to_dict()
with st.expander(f"System summary — {row['SYS_ID']} {row['System_Name']}", expanded=True):
    st.markdown(f"**What it does.** {row['System_Purpose']}.")
    sc = st.columns(4)
    sc[0].markdown(f"**Risk level**  \n{row['Risk_Level']}")
    sc[1].markdown(f"**Automated decision**  \n{row['Automated_Decision']}")
    sc[2].markdown(f"**Personal data**  \n{row['Personal_Data']}")
    sc[3].markdown(f"**Environment**  \n{row['Deployment_Env']}")
    sc2 = st.columns(3)
    sc2[0].markdown(f"**Business owner**  \n{row['Business_Owner']}")
    sc2[1].markdown(f"**Technical owner**  \n{row['Technical_Owner']}")
    sc2[2].markdown(f"**Data steward**  \n{row['Data_Steward']} ({row['Steward_Status']})")
    st.caption(f"Data inputs: {row['Data_Inputs']}  ·  lineage: {row['Lineage_Status']}  ·  "
               f"data quality: {row['DQ_Regime']}  ·  last review: "
               f"{pd.to_datetime(row['Last_Audit_Date']).date()}")

role_filter = None if ROLE == "governance" else ROLE
controls = core.system_compliance(row, sysmap, gov, g, answers, exemptions,
                                 role=role_filter, intended_use=intended_use,
                                 reviews=reviews)
summ = core.summarise(controls)
viol = core.violations(controls)

tabs = ["Questions (intake)", "My compliance", "Risk & compliance AI (chat)"]
if ROLE == "governance":
    tabs += ["Approvals & intended use", "Portfolio", "Governance readiness"]
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
        if not c["question"]:
            continue
        if c["attribute"] == "__audit_current__":
            rs = core.review_state(row, reviews)
            eff = rs["effective_date"]
            days = (dt.date.today() - eff).days if eff else None
            with st.container(border=True):
                st.markdown(f"**{c['question']}**  \n<small>{c['control']} · {c['title']} · "
                            f"status: <b>{c['status']}</b></small>", unsafe_allow_html=True)
                st.markdown(f"Effective review date: **{eff or 'none'}** "
                            f"({rs['basis']})"
                            + (f" — {days} days ago; window is {core.STALE_DAYS} days"
                               if days is not None else ""))
                cols = st.columns(2)
                for i, side_role in enumerate(("business", "technical")):
                    side = rs[side_role]
                    label = "Business owner" if side_role == "business" else "Technical owner"
                    with cols[i]:
                        if side and side.get("complete"):
                            st.success(f"{label}: completed {side['review_date']}\n\n"
                                       f"Outcome: {side['outcome']}")
                        elif side:
                            st.warning(f"{label}: started {side['review_date']}, "
                                       "not all items confirmed")
                        else:
                            st.info(f"{label}: not recorded")
                st.caption("The review counts only when both sides are complete; the "
                           "effective date is the earlier of the two.")

                if ROLE in ("business", "technical"):
                    items_def = core.REVIEW_ITEMS[ROLE]
                    prev = (rs[ROLE] or {}).get("items", {})
                    with st.expander(f"Record your side of the review ({ROLE})",
                                     expanded=not (rs[ROLE] or {}).get("complete")):
                        st.caption("Confirm each item you reviewed. All items and an "
                                   "outcome are required for your side to count.")
                        vals = {}
                        for k, lab in items_def:
                            vals[k] = st.checkbox(lab, value=bool(prev.get(k)),
                                                  key=f"rvi_{row['SYS_ID']}_{ROLE}_{k}")
                        d1, d2 = st.columns([1, 2])
                        rd_ = d1.date_input("Review date", value=dt.date.today(),
                                            key=f"rvd_{row['SYS_ID']}_{ROLE}")
                        oc_ = d2.selectbox("Review outcome", [""] + core.REVIEW_OUTCOMES,
                                           index=([""] + core.REVIEW_OUTCOMES).index(
                                               (rs[ROLE] or {}).get("outcome", "") or ""),
                                           key=f"rvo_{row['SYS_ID']}_{ROLE}")
                        nt_ = st.text_area("Findings and notes",
                                           value=(rs[ROLE] or {}).get("notes", ""),
                                           height=80, key=f"rvn_{row['SYS_ID']}_{ROLE}")
                        if st.button("Save review", key=f"rvb_{row['SYS_ID']}_{ROLE}"):
                            if not oc_:
                                st.error("Select a review outcome.")
                            else:
                                core.record_review(row["SYS_ID"], ROLE, rd_, vals, oc_,
                                                   nt_, actor)
                                st.rerun()
                else:
                    for side_role in ("business", "technical"):
                        side = rs[side_role]
                        if side and side.get("notes"):
                            st.markdown(f"**{side_role.title()} notes:** {side['notes']}")
            continue
        if c["attribute"] == "__intended_use__":
            rec = c.get("intended_use") or {}
            state = c["status"]
            sec = rec.get("sections") or {}
            gov_blk = rec.get("governance") or {}
            with st.container(border=True):
                st.markdown(f"**Intended use of the AI system**  \n<small>{c['control']} · "
                            f"{c['title']} · status: <b>{state}</b></small>",
                            unsafe_allow_html=True)
                if rec.get("legacy"):
                    st.warning("Flagged as documented in the inventory, but no document "
                               "reference exists. Record the reference or write the document.")

                # ---------- business owner ----------
                if ROLE == "business":
                    has = st.radio("Is there an intended-use document for this system?",
                                   ["Yes", "No"],
                                   index=0 if str(rec.get("has_document", "")) == "Y" else 1,
                                   horizontal=True, key=f"iuhas_{row['SYS_ID']}")
                    if has == "Yes":
                        ref = st.text_input("Document reference (ID, DMS link or version)",
                                            value=rec.get("document_ref", ""),
                                            placeholder="e.g. AI-IU-014 v1.2 / DMS link",
                                            key=f"iuref_{row['SYS_ID']}")
                        if st.button("Save", key=f"iusaveY_{row['SYS_ID']}"):
                            if not ref.strip():
                                st.error("A document reference is required for 'Yes'.")
                            else:
                                core.save_intended_use(row["SYS_ID"], "Y", ref.strip(),
                                                       sec, actor)
                                st.rerun()
                    else:
                        st.caption("Complete the document below. Sections marked * are "
                                   "required; system identification is taken from the "
                                   "inventory record.")
                        vals = {}
                        for key, label, helptext in core.OWNER_SECTIONS:
                            star = "*" if key in core.REQUIRED_SECTIONS else ""
                            vals[key] = st.text_area(f"{label}{star}", value=sec.get(key, ""),
                                                     help=helptext, height=90,
                                                     key=f"iusec_{row['SYS_ID']}_{key}")
                        if st.button("Save document", key=f"iusaveN_{row['SYS_ID']}"):
                            core.save_intended_use(row["SYS_ID"], "N", "", vals, actor)
                            st.rerun()

                # ---------- read-only view for other roles ----------
                else:
                    if str(rec.get("has_document", "")) == "Y":
                        st.markdown(f"**Document reference:** {rec.get('document_ref') or '-'}")
                    for key, label, _ in core.OWNER_SECTIONS:
                        if sec.get(key):
                            st.markdown(f"**{label}**")
                            st.write(sec[key])
                    if not sec and str(rec.get("has_document", "")) != "Y":
                        st.caption("The business owner has not recorded a document yet.")

                # ---------- governance block ----------
                st.markdown("**AI Governance Team block** "
                            "(organizational determinations - not owner-assertable)")
                if ROLE == "governance":
                    gv = {}
                    gv["risk_classification"] = st.selectbox(
                        "Risk classification", ["", "Low", "Medium", "High"],
                        index=["", "Low", "Medium", "High"].index(
                            gov_blk.get("risk_classification", "") or ""),
                        key=f"gv1_{row['SYS_ID']}")
                    gv["impact_assessment_required"] = st.selectbox(
                        "Impact assessment required?", ["", "Yes", "No"],
                        index=["", "Yes", "No"].index(
                            gov_blk.get("impact_assessment_required", "") or ""),
                        key=f"gv2_{row['SYS_ID']}")
                    gv["impact_assessment_depth"] = st.text_input(
                        "Impact assessment depth", value=gov_blk.get("impact_assessment_depth", ""),
                        placeholder="e.g. full assessment incl. societal impact; or screening only",
                        key=f"gv3_{row['SYS_ID']}")
                    gv["oversight_determination"] = st.selectbox(
                        "Human oversight determination",
                        ["", "human-in-the-loop", "human-on-the-loop", "not required"],
                        index=["", "human-in-the-loop", "human-on-the-loop",
                               "not required"].index(
                            gov_blk.get("oversight_determination", "") or ""),
                        key=f"gv4_{row['SYS_ID']}")
                    gv["prohibited_uses_policy"] = st.text_area(
                        "Prohibited uses (policy level)",
                        value=gov_blk.get("prohibited_uses_policy", ""), height=80,
                        key=f"gv5_{row['SYS_ID']}")
                    if st.button("Save governance block", key=f"gvsave_{row['SYS_ID']}"):
                        core.save_governance_block(row["SYS_ID"], gv, actor)
                        st.rerun()
                else:
                    if gov_blk.get("validated"):
                        st.success(f"Completed by {gov_blk.get('validated_by')} "
                                   f"({str(gov_blk.get('validated_at'))[:16]}).")
                        for k, label, _ in core.GOVERNANCE_FIELDS:
                            if gov_blk.get(k):
                                st.markdown(f"- **{label}:** {gov_blk[k]}")
                    else:
                        st.info("Not yet completed by the AI Governance Team.")
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
            if ROLE != "governance" and c["owner_submitted"]:
                if st.button("Clear my answer", key=f"cla_{row['SYS_ID']}_{c['attribute']}"):
                    core.clear_answer(row["SYS_ID"], c["attribute"])
                    st.rerun()
            if ROLE != "governance" and c["exemption_allowed"]:
                if c["owner_submitted"]:
                    st.caption("An answer is recorded. To claim this control is not "
                               "applicable to this system, clear your answer first.")
                else:
                    with st.expander("This control does not apply to my system"):
                        j = st.text_area("Justification (required)",
                                         key=f"j_{row['SYS_ID']}_{c['control']}",
                                         placeholder="e.g. this system produces no automated "
                                                     "decisions, so human oversight of "
                                                     "automated decisions does not apply.")
                        if st.button("Submit N/A claim for review",
                                     key=f"cl_{row['SYS_ID']}_{c['control']}"):
                            if not j.strip():
                                st.error("A justification is required.")
                            else:
                                core.claim_exemption(row["SYS_ID"], c["control"], j,
                                                     ROLE, actor)
                                core.clear_answer(row["SYS_ID"], c["attribute"])
                                st.rerun()

# ---------------- compliance ----------------
with T[1]:
    st.subheader(f"{row['System_Name']} — compliance")
    st.caption("System details are in the summary panel above.")
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
    if summ.get("awaiting"):
        st.info(f"{summ['awaiting']} intended-use statement(s) awaiting AI Governance approval.")
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
    st.caption(f"Ask about **{row['System_Name']}** - its violations, what a control "
               f"requires, how to fix something - or ask about the organisation's policies "
               f"and procedures. Answers are grounded in retrieved extracts from the "
               f"{len(set(c['doc_id'] for c in generation.retrieval.load_corpus_chunks()))}"
               f"-document policy corpus plus this system's control status. "
               f"Backend: **{backend}**.")

    key = f"chat_{row['SYS_ID']}_{ROLE}"
    if key not in st.session_state:
        st.session_state[key] = []

    c1, c2 = st.columns([3, 1])
    if c1.button("Draft a remediation plan for this system"):
        with st.spinner("Generating..."):
            res = generation.draft_remediation(sysd, viol, backend=backend)
        st.session_state[key].append({"role": "user",
                                      "content": "Draft a remediation plan for this system."})
        st.session_state[key].append({"role": "assistant", "content": res["report"],
                                      "meta": res})
    if c2.button("Clear chat"):
        st.session_state[key] = []
        st.rerun()

    for turn in st.session_state[key]:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])
            m = turn.get("meta")
            if m:
                ct = m.get("completion_tokens")
                st.caption(f"backend: {m['backend']} · model: {m['model']} · prompt tokens "
                           f"~ {m['prompt_tokens']} · completion tokens: "
                           f"{ct if ct is not None else 'n/a'}")
                rt = m.get("retrieved") or {}
                if rt.get("corpus"):
                    st.caption("Sources retrieved from the policy corpus: "
                               + ", ".join(sorted({f"{c['doc_id']}" for c in rt["corpus"]})))
                if rt.get("inherited"):
                    st.caption("Inherited controls added by knowledge-graph traversal: "
                               + ", ".join(c["control"] for c in rt["inherited"]))
                with st.expander("Context sent to the LLM (retrieved grounding)"):
                    st.code(m["system_prompt"] + "\n\n" + m["prompt"])

    q = st.chat_input(f"Ask about {row['System_Name']}...")
    if q:
        st.session_state[key].append({"role": "user", "content": q})
        with st.spinner("Thinking..."):
            res = generation.answer_question(sysd, controls, q,
                                             history=st.session_state[key][:-1],
                                             backend=backend, graph=g)
        st.session_state[key].append({"role": "assistant", "content": res["report"],
                                      "meta": res})
        st.rerun()

    if st.session_state[key]:
        transcript = "\n\n".join(f"**{x['role']}:** {x['content']}"
                                  for x in st.session_state[key])
        st.download_button("Download conversation (.md)", transcript,
                           file_name=f"qa_{row['SYS_ID']}.md")

# ---------------- governance-only ----------------
if ROLE == "governance":
    with T[3]:
        st.subheader("Intended use - governance block outstanding")
        st.caption("The business owner records or writes the intended-use document. The AI "
                   "Governance Team does not approve its content, but must complete the "
                   "fields only it can determine: risk classification, impact-assessment "
                   "requirement and depth, oversight determination, and policy-level "
                   "prohibited uses. A.9.4 is compliant when a document exists AND this "
                   "block is complete. Open a system from the sidebar to fill it in.")
        outstanding = core.pending_governance_block(inv, intended_use)
        if not outstanding:
            st.info("No systems are waiting on the governance block.")
        else:
            st.dataframe(pd.DataFrame([{"SYS_ID": r_["sys_id"], "System": r_["system"],
                                        "Risk": r_["risk"],
                                        "Business owner": r_["business_owner"],
                                        "Document": ("reference recorded"
                                                     if r_["has_document"] == "Y"
                                                     else ("written in app" if r_["sections"]
                                                           else "inventory flag only")),
                                        "State": r_["state"]} for r_ in outstanding]),
                         use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Intended-use register - all systems")
        reg = core.intended_use_register(inv, intended_use)
        counts = {}
        for r_ in reg:
            counts[r_["state"]] = counts.get(r_["state"], 0) + 1
        mm = st.columns(4)
        mm[0].metric("Complete", counts.get("complete", 0))
        mm[1].metric("Governance block pending",
                     counts.get("document_only", 0) + counts.get("legacy", 0))
        mm[2].metric("Document in progress", counts.get("drafting", 0))
        mm[3].metric("Not started", counts.get("none", 0))
        _pp = {r.SYS_ID: r.System_Purpose for r in inv.itertuples()}
        st.dataframe(pd.DataFrame([{"SYS_ID": r_["sys_id"], "System": r_["system"],
                                    "What it does": _pp.get(r_["sys_id"], ""),
                                    "Risk": r_["risk"],
                                    "Business owner": r_["business_owner"],
                                    "Intended use": r_["state"],
                                    "Document ref": r_["document_ref"],
                                    "Governance block by": r_["validated_by"]}
                                   for r_ in reg]),
                     use_container_width=True, hide_index=True)
        readable = [r_ for r_ in reg if r_["sections"] or r_["document_ref"]]
        if readable:
            st.markdown("**Read a document**")
            labels = [f"{r_['sys_id']} - {r_['system']}" for r_ in readable]
            sel = st.selectbox("System", labels, key="iu_read")
            ch = readable[labels.index(sel)]
            if ch["document_ref"]:
                st.markdown(f"**Document reference:** {ch['document_ref']}")
            for key, label, _ in core.OWNER_SECTIONS:
                if ch["sections"].get(key):
                    st.markdown(f"**{label}**")
                    st.write(ch["sections"][key])
            gblk = ch["governance"]
            if gblk:
                st.markdown("**AI Governance Team block**")
                for k, label, _ in core.GOVERNANCE_FIELDS:
                    if gblk.get(k):
                        st.markdown(f"- **{label}:** {gblk[k]}")

        st.divider()
        st.subheader("Exemption reviews - AI Governance Team")
        st.caption("Owners claim a control is not applicable to their system; you decide. "
                   "Approved claims are excluded from that system's scoring and recorded "
                   "with the justification and approver (per-system Statement of "
                   "Applicability trail).")
        _purpose = {r.SYS_ID: (r.System_Name, r.System_Purpose, r.Risk_Level,
                              r.Automated_Decision, r.Personal_Data)
                    for r in inv.itertuples()}
        queue = core.pending_exemptions(inv, exemptions, sysmap)
        if not queue:
            st.info("No pending claims.")
        for q in queue:
            with st.container(border=True):
                st.markdown(f"**{q['sys_id']} {q['system']} — {q['control']} {q['title']}**  \n"
                            f"<small>claimed by {q['claimed_by']} ({q['claimed_role']}) on "
                            f"{q['claimed_at'][:16]}</small>", unsafe_allow_html=True)
                _p = _purpose.get(q["sys_id"])
                if _p:
                    st.info(f"**What this system does.** {_p[1]}.  \n"
                            f"Risk: {_p[2]} · automated decision: {_p[3]} · "
                            f"personal data: {_p[4]}")
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
            ctrls = core.system_compliance(rd, sysmap, gov, g, answers, exemptions,
                                          intended_use=intended_use, reviews=reviews)
            s = core.summarise(ctrls)
            _iu_state, _ = core.intended_use_status(rd["SYS_ID"], rd, intended_use)
            rows.append({"SYS_ID": r.SYS_ID, "System": r.System_Name,
                         "What it does": r.System_Purpose,
                         "Risk": r.Risk_Level,
                         "Applicable": s["applicable"], "Compliant": s["compliant"],
                         "Violations": s["violations"], "Not answered": s["unanswered"],
                         "N/A pending": s["na_pending"], "N/A approved": s["na_approved"],
                         "Not required": s["not_required"],
                         "Awaiting approval": s.get("awaiting", 0),
                         "Intended use": _iu_state,
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
        st.caption("Is our policy/procedure set itself complete against Annex A? The AI "
                   "Governance Team assigns each gap to the responsible department and "
                   "tracks closure. Assessed once org-wide - not per system.")
        actions = core.load_policy_actions()
        rd = core.governance_readiness(gov, actions, procmap)
        gaps = [r for r in rd if r["policy_status"] == "gap"]
        m = st.columns(4)
        m[0].metric("Annex A controls", len(rd))
        m[1].metric("Policy evidence present", len(rd) - len(gaps))
        m[2].metric("Policy gaps", len(gaps))
        m[3].metric("Gaps assigned", len([r for r in gaps if r["assigned_to"]]))

        st.markdown("**Assign / track policy gaps**")
        for r in gaps:
            with st.container(border=True):
                st.markdown(f"**{r['control_id']} — {r['title']}**  \n"
                            f"<small>status: {r['action_status'] or 'Unassigned'}"
                            + (f" · owner: {r['assigned_to']}" if r["assigned_to"] else "")
                            + (f" · due: {r['due_date']}" if r["due_date"] else "")
                            + "</small>", unsafe_allow_html=True)
                if r["owner_update"]:
                    st.success(f"Owner update ({r['updated_by']}): {r['owner_update']}"
                               + (f"  \nDocument: {r['evidence_ref']}" if r["evidence_ref"] else ""))
                c1, c2 = st.columns([2, 1])
                if r.get("proposed_procedure"):
                    st.caption(f"Proposed procedure: **{r['proposed_procedure']}** "
                               f"({r.get('new_or_addition','')}) · recommended owner: "
                               f"{r.get('recommended_owner','-')}"
                               + (f" · contributing: {r['contributing_owner']}"
                                  if r.get("contributing_owner") else ""))
                _pref = r["assigned_to"] or r.get("recommended_owner", "")
                dept = c1.selectbox("Responsible department", [""] + core.PROCEDURE_OWNERS,
                                    index=(core.PROCEDURE_OWNERS.index(_pref) + 1)
                                    if _pref in core.PROCEDURE_OWNERS else 0,
                                    key=f"ga_{r['control_id']}")
                due = c2.text_input("Due date", value=r["due_date"],
                                    placeholder="YYYY-MM-DD", key=f"gd_{r['control_id']}")
                note = st.text_input("Instruction to the department "
                                     "(new procedure, or addition to an existing one?)",
                                     value=r["governance_note"], key=f"gn_{r['control_id']}")
                b1, b2 = st.columns(2)
                if b1.button("Assign / update", key=f"gb_{r['control_id']}"):
                    if not dept:
                        st.error("Select a responsible department.")
                    else:
                        core.assign_policy_action(r["control_id"], dept, note, due, actor)
                        st.success(f"Assigned to {dept}.")
                        st.rerun()
                if r["assigned_to"] and b2.button("Clear assignment",
                                                  key=f"gc_{r['control_id']}"):
                    core.clear_policy_action(r["control_id"])
                    st.rerun()

        st.divider()
        st.markdown("### Raise a procedure update request")
        st.caption("Use this to ask a directorate for an addition that is not tied to a "
                   "specific Annex A gap above. The request appears on that directorate's "
                   "own page, where they record what they added.")
        with st.form("newreq", clear_on_submit=True):
            f1, f2 = st.columns(2)
            r_owner = f1.selectbox("Procedure owner", core.PROCEDURE_OWNERS)
            r_ctrl = f2.text_input("Related Annex A control (optional)",
                                   placeholder="e.g. A.7.4")
            r_proc = st.text_input("Procedure", placeholder="e.g. PR-SEC-002 Log Management")
            r_sect = st.text_input("Section (optional)", placeholder="e.g. 2.3")
            r_add = st.text_area("Requested addition", height=110,
                                 placeholder="Describe the provision the procedure owner "
                                             "should draft and publish.")
            r_due = st.text_input("Due date (optional)", placeholder="YYYY-MM-DD")
            if st.form_submit_button("Send request"):
                if not (r_proc.strip() and r_add.strip()):
                    st.error("Procedure and requested addition are required.")
                else:
                    core.create_proc_request(r_owner, r_proc.strip(), r_sect.strip(),
                                             r_add.strip(), r_ctrl.strip(), r_due.strip(),
                                             actor)
                    st.success(f"Request sent to {r_owner}.")
                    st.rerun()

        allreq = core.load_proc_requests()
        if allreq:
            st.markdown("**Requests raised**")
            st.dataframe(pd.DataFrame([{"ID": r["id"], "Owner": r["owner"],
                                        "Procedure": r["procedure"],
                                        "Control": r["control"], "Due": r["due_date"],
                                        "Status": r["status"],
                                        "Owner response": r["owner_response"]}
                                       for r in allreq.values()]),
                         use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("**Full Annex A readiness**")
        st.dataframe(pd.DataFrame([{"control": r["control_id"], "title": r["title"],
                                    "policy status": r["policy_status"],
                                    "proposed procedure": r.get("proposed_procedure", ""),
                                    "new / addition": r.get("new_or_addition", ""),
                                    "recommended owner": r.get("recommended_owner", ""),
                                    "assigned to": r["assigned_to"],
                                    "action status": r["action_status"],
                                    "due": r["due_date"],
                                    "owner update": r["owner_update"]} for r in rd]),
                     use_container_width=True, hide_index=True)
        st.divider()
        st.markdown("**Per-system control scope & justification**")
        st.caption("Why each control is assessed per system.")
        st.dataframe(pd.DataFrame([{"control": r["control_id"], "title": r["title"],
                                    "scope": r.get("scope", ""),
                                    "N/A claim allowed": r.get("exemption_allowed", ""),
                                    "justification": r.get("per_system_justification", "")}
                                   for r in sysmap]),
                     use_container_width=True, hide_index=True)
