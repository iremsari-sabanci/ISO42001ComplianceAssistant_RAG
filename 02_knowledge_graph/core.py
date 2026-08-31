"""Shared compliance core: data loading, per-system compliance, owner answers, exemptions.

Four control statuses:
  Compliant              answered with the compliant value
  Violation              answered with a non-compliant value
  Not answered           intake gap - no answer yet (distinct from a "No")
  N/A pending review     owner claimed not-applicable with a justification; awaiting AI Gov review
  N/A approved           AI Governance Team accepted the claim; excluded from scoring
  Response not required  shown for transparency, but ISO 42001 does not require an answer for
                         THIS system (e.g. human oversight where no automated decision is made);
                         an on-screen note explains why. Optional to answer.

Only Violation counts against a system. "Not answered" and "N/A pending" are tracked
separately so a green score cannot be manufactured by claiming exemptions or by silence.
"""
import os, csv, json
import datetime as dt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
INV = os.path.join(HERE, "..", "01_inventory", "AI_System_Inventory.xlsx")
SYSMAP = os.path.join(HERE, "..", "04_ground_truth", "system_control_map.csv")
GOV = os.path.join(HERE, "..", "04_ground_truth", "control_evidence_map.csv")
PROCMAP = os.path.join(HERE, "..", "04_ground_truth", "procedure_responsibility_map.csv")
ANSWERS = os.path.join(HERE, "..", "01_inventory", "owner_answers.json")
EXEMPTIONS = os.path.join(HERE, "..", "01_inventory", "exemption_claims.json")
POLICY_ACTIONS = os.path.join(HERE, "..", "01_inventory", "policy_actions.json")
INTENDED_USE = os.path.join(HERE, "..", "01_inventory", "intended_use.json")
REVIEWS = os.path.join(HERE, "..", "01_inventory", "system_reviews.json")
PROC_REQUESTS = os.path.join(HERE, "..", "01_inventory", "procedure_requests.json")
STALE_DAYS = 180

# Departments that can own a policy/procedure action (Procedure Owner role).
PROCEDURE_OWNERS = [
    "AI Governance Team (Data Management and Analytics Directorate)",
    "Artificial Intelligence Solutions Directorate",
    "Data Management and Analytics Directorate",
    "IT Infrastructure and Operations Directorate",
    "Information Security Directorate",
    "IT Strategy and Governance Directorate",
]

POLICY_ACTION_STATUS = ["Open", "In progress", "Drafted - in review", "Completed"]

ST_COMPLIANT = "Compliant"
ST_VIOLATION = "Violation"
ST_UNANSWERED = "Not answered"
ST_NA_PENDING = "N/A pending review"
ST_NA_APPROVED = "N/A approved"
ST_NOT_REQUIRED = "Response not required"
ST_AWAITING = "Awaiting governance approval"
ST_DRAFTING = "Document in progress"
ST_GOV_PENDING = "Governance block incomplete"


def load_inventory():
    df = pd.read_excel(INV, sheet_name="Inventory", header=3, engine="openpyxl")
    return df[df["SYS_ID"].notna()].reset_index(drop=True)


def load_sysmap():
    with open(SYSMAP, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_gov():
    with open(GOV, newline="", encoding="utf-8") as f:
        return {r["control_id"]: r for r in csv.DictReader(f)}


def load_procmap():
    """Proposed procedure + recommended owning directorate for each Annex A control."""
    with open(PROCMAP, newline="", encoding="utf-8") as f:
        return {r["control_id"]: r for r in csv.DictReader(f)}


def _read(path):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _write(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------- owner answers
def load_answers():
    return _read(ANSWERS)


def save_answer(sys_id, attribute, value, role, actor=""):
    data = load_answers()
    data.setdefault(sys_id, {})[attribute] = {
        "value": value, "role": role, "actor": actor,
        "updated": dt.datetime.now().isoformat(timespec="seconds")}
    _write(ANSWERS, data)
    return data


def clear_answer(sys_id, attribute):
    data = load_answers()
    if sys_id in data and attribute in data[sys_id]:
        del data[sys_id][attribute]
        _write(ANSWERS, data)
    return data


# ---------------------------------------------------------------- exemption claims
def load_exemptions():
    return _read(EXEMPTIONS)


def claim_exemption(sys_id, control_id, justification, role, actor=""):
    """Owner claims a control is not applicable to this system. Requires justification."""
    if not (justification or "").strip():
        raise ValueError("A justification is required to claim 'not applicable'.")
    data = load_exemptions()
    data.setdefault(sys_id, {})[control_id] = {
        "status": "pending", "justification": justification.strip(),
        "claimed_by": actor, "claimed_role": role,
        "claimed_at": dt.datetime.now().isoformat(timespec="seconds"),
        "reviewed_by": "", "reviewed_at": "", "review_note": ""}
    _write(EXEMPTIONS, data)
    return data


def review_exemption(sys_id, control_id, decision, reviewer, note=""):
    """AI Governance Team adjudicates: decision in {'approved','rejected'}."""
    data = load_exemptions()
    rec = (data.get(sys_id) or {}).get(control_id)
    if not rec:
        return data
    rec.update(status=decision, reviewed_by=reviewer, review_note=note,
               reviewed_at=dt.datetime.now().isoformat(timespec="seconds"))
    _write(EXEMPTIONS, data)
    return data


def withdraw_exemption(sys_id, control_id):
    data = load_exemptions()
    if sys_id in data and control_id in data[sys_id]:
        del data[sys_id][control_id]
        _write(EXEMPTIONS, data)
    return data


def pending_exemptions(inv, exemptions, sysmap):
    """Queue for the AI Governance Team: all pending claims across systems."""
    title = {r["control_id"]: r["title"] for r in sysmap}
    names = {r["SYS_ID"]: r["System_Name"] for _, r in inv.iterrows()}
    out = []
    for sid, ctrls in (exemptions or {}).items():
        for cid, rec in ctrls.items():
            if rec.get("status") == "pending":
                out.append({"sys_id": sid, "system": names.get(sid, sid), "control": cid,
                            "title": title.get(cid, ""), **rec})
    return out


# ------------------------------------------------- intended-use document (A.9.4)
# Headings the business owner completes when authoring in-app. System identification is
# taken from the inventory record and is not re-keyed.
OWNER_SECTIONS = [
    ("purpose_rationale", "Purpose and rationale",
     "Why the system was built: the business need, customer demand or regulatory driver."),
    ("intended_users", "Intended users and affected parties",
     "Who operates the system, and which interested parties are affected by its outputs."),
    ("intended_use", "Intended use",
     "The decisions or processes the system supports and how its outputs are consumed."),
    ("scope_of_application", "Scope of application",
     "Operational domain it is valid for: customer segments, products, channels, "
     "languages, geography."),
    ("data_used", "Data used",
     "Categories and sources of data, including any personal or special-category data."),
    ("technical_assumptions", "Technical assumptions and prerequisites",
     "Runtime environment, integrations, and assumptions made about input data."),
    ("limitations", "Limitations and performance boundaries",
     "Accuracy and acceptable error rates; conditions under which performance degrades."),
    ("human_oversight_practice", "Human oversight in practice",
     "Who performs oversight and how an output is overridden or the system disabled."),
    ("monitoring_review", "Monitoring and review triggers",
     "What is monitored, and what changes require revalidation or a new impact assessment."),
    ("related_records", "Related records",
     "References to impact assessment, verification and validation results, technical "
     "documentation and KVKK records."),
]
# minimum set required before the document counts as written
REQUIRED_SECTIONS = ["purpose_rationale", "intended_users", "intended_use",
                     "scope_of_application", "limitations"]

# Fields only the AI Governance Team can determine (organizational determinations).
GOVERNANCE_FIELDS = [
    ("risk_classification", "Risk classification",
     "Confirmed risk level for this system; drives which controls apply."),
    ("impact_assessment_required", "Impact assessment required?",
     "Whether an AI system impact assessment is required for this system (Clause 8.4)."),
    ("impact_assessment_depth", "Impact assessment depth",
     "How detailed the assessment must be (B.5.2 conditions: criticality, automation "
     "level, data sensitivity)."),
    ("oversight_determination", "Human oversight determination",
     "Whether oversight is necessary and in what form (in-the-loop / on-the-loop / not "
     "required) - an organizational determination per B.9.3."),
    ("prohibited_uses_policy", "Prohibited uses (policy level)",
     "Uses ruled out by organizational policy rather than by the system itself."),
]


def load_intended_use():
    return _read(INTENDED_USE)


def _blank(sys_id):
    return {"has_document": "", "document_ref": "", "sections": {},
            "governance": {}, "owner_updated_by": "", "owner_updated_at": ""}


def save_intended_use(sys_id, has_document, document_ref, sections, actor):
    """Business owner records whether a document exists, or authors one in-app."""
    d = load_intended_use()
    rec = d.get(sys_id) or _blank(sys_id)
    rec.update({"has_document": has_document, "document_ref": document_ref,
                "sections": sections or rec.get("sections", {}),
                "owner_updated_by": actor,
                "owner_updated_at": dt.datetime.now().isoformat(timespec="seconds")})
    rec.setdefault("governance", {})
    d[sys_id] = rec
    _write(INTENDED_USE, d)
    return d


def save_governance_block(sys_id, values, actor):
    """AI Governance Team completes the fields only it can determine."""
    d = load_intended_use()
    rec = d.get(sys_id) or _blank(sys_id)
    gov = rec.get("governance", {})
    gov.update(values)
    complete = all(str(gov.get(k, "")).strip() for k, _, _ in GOVERNANCE_FIELDS
                   if not (k == "impact_assessment_depth"
                           and str(gov.get("impact_assessment_required", "")).strip() == "No"))
    gov.update({"validated": complete, "validated_by": actor if complete else "",
                "validated_at": dt.datetime.now().isoformat(timespec="seconds")
                if complete else ""})
    rec["governance"] = gov
    d[sys_id] = rec
    _write(INTENDED_USE, d)
    return d


def document_present(rec):
    """Does an intended-use document exist - either referenced externally or written here?"""
    if not rec:
        return False
    if str(rec.get("has_document", "")).strip() == "Y":
        return bool(str(rec.get("document_ref", "")).strip())
    s = rec.get("sections") or {}
    return all(str(s.get(k, "")).strip() for k in REQUIRED_SECTIONS)


def intended_use_status(sys_id, row, iu):
    """Resolve A.9.4: needs a document AND a complete governance block."""
    rec = (iu or {}).get(sys_id)
    if rec:
        doc = document_present(rec)
        val = bool((rec.get("governance") or {}).get("validated"))
        if doc and val:
            return "complete", rec
        if doc:
            return "document_only", rec
        if str(rec.get("has_document", "")).strip() == "N" or (rec.get("sections") or {}):
            return "drafting", rec
        return "none", rec
    if str(row.get("Intended_Use_Doc", "")).strip() == "Y":
        return "legacy", {"has_document": "Y", "document_ref": "(flagged in the inventory; "
                          "no document reference recorded)", "sections": {},
                          "governance": {}, "legacy": True}
    return "none", rec or {}


def intended_use_register(inv, iu):
    out = []
    for _, r in inv.iterrows():
        row = r.to_dict()
        state, rec = intended_use_status(row["SYS_ID"], row, iu)
        gov = (rec or {}).get("governance", {})
        out.append({"sys_id": row["SYS_ID"], "system": row["System_Name"],
                    "business_owner": row["Business_Owner"], "risk": row["Risk_Level"],
                    "state": state,
                    "has_document": (rec or {}).get("has_document", ""),
                    "document_ref": (rec or {}).get("document_ref", ""),
                    "sections": (rec or {}).get("sections", {}),
                    "governance": gov,
                    "validated_by": gov.get("validated_by", ""),
                    "validated_at": str(gov.get("validated_at", ""))[:16],
                    "owner_updated_by": (rec or {}).get("owner_updated_by", ""),
                    "legacy": bool((rec or {}).get("legacy"))})
    return out


def pending_governance_block(inv, iu):
    """Systems with a document recorded but the governance block still incomplete."""
    return [r for r in intended_use_register(inv, iu)
            if r["state"] in ("document_only", "legacy")]


# ------------------------------------------------- policy actions (Governance readiness)
def load_policy_actions():
    return _read(POLICY_ACTIONS)


def assign_policy_action(control_id, department, note, due_date, actor):
    """AI Governance Team assigns an Annex A policy gap to the responsible department."""
    data = load_policy_actions()
    rec = data.get(control_id, {})
    rec.update({"assigned_to": department, "assigned_by": actor,
                "assigned_at": dt.datetime.now().isoformat(timespec="seconds"),
                "governance_note": note, "due_date": due_date,
                "status": rec.get("status", "Open"),
                "owner_update": rec.get("owner_update", ""),
                "evidence_ref": rec.get("evidence_ref", ""),
                "updated_by": rec.get("updated_by", ""),
                "updated_at": rec.get("updated_at", "")})
    data[control_id] = rec
    _write(POLICY_ACTIONS, data)
    return data


def update_policy_action(control_id, status, owner_update, evidence_ref, actor):
    """Procedure Owner records progress on an assigned policy gap."""
    data = load_policy_actions()
    rec = data.setdefault(control_id, {})
    rec.update({"status": status, "owner_update": owner_update,
                "evidence_ref": evidence_ref, "updated_by": actor,
                "updated_at": dt.datetime.now().isoformat(timespec="seconds")})
    _write(POLICY_ACTIONS, data)
    return data


def clear_policy_action(control_id):
    data = load_policy_actions()
    if control_id in data:
        del data[control_id]
        _write(POLICY_ACTIONS, data)
    return data


# ---- free-form procedure update requests raised by the AI Governance Team ----
PROC_REQUEST_STATUS = ["Open", "Acknowledged", "In progress", "Drafted - in review",
                       "Published", "Declined"]


def load_proc_requests():
    return _read(PROC_REQUESTS)


def create_proc_request(owner, procedure, section, addition, control, due, actor):
    d = load_proc_requests()
    rid = f"REQ-{len(d) + 1:03d}"
    while rid in d:
        rid = f"REQ-{int(rid.split('-')[1]) + 1:03d}"
    d[rid] = {"id": rid, "owner": owner, "procedure": procedure, "section": section,
              "addition": addition, "control": control, "due_date": str(due or ""),
              "status": "Open", "created_by": actor,
              "created_at": dt.datetime.now().isoformat(timespec="seconds"),
              "owner_response": "", "responded_by": "", "responded_at": ""}
    _write(PROC_REQUESTS, d)
    return d


def respond_proc_request(rid, status, response, actor):
    d = load_proc_requests()
    r = d.get(rid)
    if not r:
        return d
    r.update({"status": status, "owner_response": response, "responded_by": actor,
              "responded_at": dt.datetime.now().isoformat(timespec="seconds")})
    _write(PROC_REQUESTS, d)
    return d


def delete_proc_request(rid):
    d = load_proc_requests()
    d.pop(rid, None)
    _write(PROC_REQUESTS, d)
    return d


def proc_requests_for(owner, requests=None):
    return [r for r in (requests or load_proc_requests()).values()
            if r["owner"] == owner]


def governance_readiness(gov, actions, procmap=None):
    """Annex A policy coverage joined with assignment/progress state."""
    out = []
    for cid, r in gov.items():
        a = actions.get(cid, {})
        pm = (procmap or {}).get(cid, {})
        out.append({"control_id": cid, "title": r["title"],
                    "proposed_procedure": pm.get("proposed_procedure", ""),
                    "recommended_owner": pm.get("primary_owner", ""),
                    "contributing_owner": pm.get("contributing_owner", ""),
                    "new_or_addition": pm.get("new_or_addition", ""),
                    "policy_status": r["evidence_status"],
                    "evidence": r["evidence_source"],
                    "assigned_to": a.get("assigned_to", ""),
                    "due_date": a.get("due_date", ""),
                    "action_status": a.get("status", "" if r["evidence_status"] != "gap" else "Unassigned"),
                    "governance_note": a.get("governance_note", ""),
                    "owner_update": a.get("owner_update", ""),
                    "evidence_ref": a.get("evidence_ref", ""),
                    "updated_by": a.get("updated_by", "")})
    return out


# ---------------------------------------------------------------- compliance
def effective_value(row, attribute, answers):
    sid = row.get("SYS_ID")
    a = (answers.get(sid) or {}).get(attribute)
    if a and str(a.get("value", "")).strip():
        return str(a["value"]).strip(), True
    return "", False   # inventory value is a starting point only; see system_compliance


# Operational review (A.6.2.6). Items follow B.6.2.6: system and performance monitoring,
# repairs, updates and support - split by who can actually answer them.
REVIEW_ITEMS = {
    "business": [
        ("intended_purpose", "Still used for its documented intended purpose; no new or "
         "unforeseen use has appeared"),
        ("scope_change", "Scope reviewed: customer segments, products, channels, geographies"),
        ("user_feedback", "Concerns, complaints or feedback from users and affected parties "
         "reviewed"),
        ("oversight_working", "Human oversight operating as defined; override frequency "
         "reviewed"),
        ("regulatory_change", "Regulatory, contractual or policy changes affecting the use "
         "case considered"),
        ("benefit_realised", "Use case still needed and delivering its intended benefit"),
    ],
    "technical": [
        ("performance", "Performance against acceptance criteria reviewed (error rates, "
         "confidence, stability on production data)"),
        ("drift", "Data and concept drift assessed; need for retraining considered"),
        ("incidents", "Errors, failures and incidents in the period reviewed, with repairs"),
        ("updates", "Updates and model versions released; users informed of operational "
         "changes"),
        ("logging", "Event logging still enabled and complete"),
        ("ai_security", "AI-specific security threats reviewed (data poisoning, model theft, "
         "model inversion)"),
    ],
}
REVIEW_OUTCOMES = [
    "Continue unchanged",
    "Remediate - actions raised",
    "Revalidate (verification and validation)",
    "New impact assessment required",
    "Refer for retirement",
]


def load_reviews():
    return _read(REVIEWS)


def record_review(sys_id, role, review_date, items, outcome, notes, actor):
    """Record one side (business or technical) of the operational review."""
    d = load_reviews()
    rec = d.get(sys_id, {})
    side = {"review_date": str(review_date), "items": items, "outcome": outcome,
            "notes": notes, "recorded_by": actor,
            "recorded_at": dt.datetime.now().isoformat(timespec="seconds"),
            "complete": bool(outcome) and all(items.get(k) for k, _ in REVIEW_ITEMS[role])}
    rec[role] = side
    hist = rec.get("history", [])
    hist.insert(0, {"role": role, **side})
    rec["history"] = hist[:20]
    d[sys_id] = rec
    _write(REVIEWS, d)
    return d


def review_state(row, reviews=None):
    """Combined state of the operational review for one system."""
    rec = (reviews or {}).get(row.get("SYS_ID"), {})
    out = {"business": rec.get("business"), "technical": rec.get("technical"),
           "inventory_date": None, "effective_date": None, "basis": "none"}
    try:
        out["inventory_date"] = pd.to_datetime(row["Last_Audit_Date"]).date()
    except Exception:
        pass
    def _d(side):
        try:
            return pd.to_datetime(side["review_date"]).date() if side else None
        except Exception:
            return None
    b, tch = out["business"], out["technical"]
    bd, td = _d(b), _d(tch)
    if b and tch and b.get("complete") and tch.get("complete") and bd and td:
        out["effective_date"] = min(bd, td); out["basis"] = "joint review"
    else:
        out["effective_date"] = out["inventory_date"]
        out["basis"] = "inventory record" if out["inventory_date"] else "none"
    return out


def last_review_date(row, reviews=None):
    return review_state(row, reviews)["effective_date"]


def audit_current(row, reviews=None):
    d = last_review_date(row, reviews)
    return bool(d) and (dt.date.today() - d).days <= STALE_DAYS


def _is_compliant(val, rule):
    """compliant_if may list several acceptable values separated by ';'."""
    ok = [v.strip() for v in str(rule["compliant_if"]).split(";") if v.strip()]
    return val in ok


def required(rule, row):
    """Is an answer mandatory for THIS system? Defaults to applies_when."""
    w = rule.get("required_when") or rule.get("applies_when", "all")
    auto = str(row.get("Automated_Decision", "")).strip() == "Y"
    pii = str(row.get("Personal_Data", "")).strip() == "Y"
    return {"all": True, "auto": auto, "pii": pii, "auto_or_pii": auto or pii}.get(w, True)


def applies(rule, row):
    w = rule["applies_when"]
    auto = str(row.get("Automated_Decision", "")).strip() == "Y"
    pii = str(row.get("Personal_Data", "")).strip() == "Y"
    return {"all": True, "auto": auto, "pii": pii, "auto_or_pii": auto or pii}.get(w, True)


def system_compliance(row, sysmap, gov, g, answers=None, exemptions=None, role=None,
                      intended_use=None, reviews=None):
    answers = answers or {}
    exemptions = exemptions or {}
    sid = row.get("SYS_ID")
    ex_sys = exemptions.get(sid, {})
    cur = audit_current(row, reviews)
    out = []
    for rule in sysmap:
        if not applies(rule, row):
            continue
        if role and rule.get("owner_role") != role:
            continue
        cid, attr = rule["control_id"], rule["attribute"]
        req = required(rule, row)

        # owner answer wins; otherwise fall back to the inventory's recorded value
        iu_rec = None
        if attr == "__intended_use__":
            iu_state, iu_rec = intended_use_status(sid, row, intended_use)
            val = {"complete": "Y", "document_only": "document_only",
                   "legacy": "legacy", "drafting": "drafting"}.get(iu_state, "")
            submitted = iu_state in ("complete", "document_only", "drafting", "legacy")
        elif attr == "__audit_current__":
            val, submitted = ("Y" if cur else "N"), False
        else:
            val, submitted = effective_value(row, attr, answers)
            if not val:
                val = str(row.get(attr, "")).strip()
                # a recorded "n/a" in the seeded inventory is legacy: treat as unanswered
                # legacy blanks from the seeded workbook -> unanswered.
                # NB: "none" is a legitimate answer value (oversight mode), not a blank.
                if val.lower() in ("n/a", "na", "nan"):
                    val = ""

        ex = ex_sys.get(cid)
        if ex and ex.get("status") == "approved":
            status = ST_NA_APPROVED
        elif ex and ex.get("status") == "pending":
            status = ST_NA_PENDING
        elif attr == "__intended_use__" and val in ("document_only", "legacy"):
            status = ST_GOV_PENDING
        elif attr == "__intended_use__" and val == "drafting":
            status = ST_DRAFTING
        elif not val:
            status = ST_UNANSWERED if req else ST_NOT_REQUIRED
        elif _is_compliant(val, rule):
            status = ST_COMPLIANT
        else:
            status = ST_VIOLATION if req else ST_NOT_REQUIRED

        out.append({
            "control": cid, "title": rule["title"], "status": status,
            "current": f"{rule['current_label']}: {val or '(not answered)'}",
            "value": val, "attribute": attr,
            "owner_role": rule.get("owner_role", "business"),
            "question": rule.get("question", ""),
            "options": [o for o in (rule.get("options", "") or "").split("|") if o],
            "compliant_if": rule["compliant_if"],
            "scope": rule.get("scope", "system"),
            "exemption_allowed": rule.get("exemption_allowed", "N") == "Y",
            "justification": rule.get("per_system_justification", ""),
            "required": req,
            "intended_use": iu_rec,
            "not_required_note": rule.get("not_required_note", ""),
            "exemption": ex or None,
            "requirement": g.nodes[cid].get("clause_summary", "") if cid in g.nodes else "",
            "policy_ref": gov.get(cid, {}).get("evidence_source", ""),
            "owner_submitted": submitted,
        })
    return out


def violations(controls):
    return [c for c in controls if c["status"] == ST_VIOLATION]


def unanswered(controls):
    return [c for c in controls if c["status"] == ST_UNANSWERED]


def na_pending(controls):
    return [c for c in controls if c["status"] == ST_NA_PENDING]


def na_approved(controls):
    return [c for c in controls if c["status"] == ST_NA_APPROVED]


def drafting(controls):
    return [c for c in controls if c["status"] == ST_DRAFTING]


def awaiting_approval(controls):
    return [c for c in controls if c["status"] in (ST_AWAITING, ST_GOV_PENDING)]


def not_required(controls):
    return [c for c in controls if c["status"] == ST_NOT_REQUIRED]


def compliant(controls):
    return [c for c in controls if c["status"] == ST_COMPLIANT]


def summarise(controls):
    return {"applicable": len(controls), "compliant": len(compliant(controls)),
            "violations": len(violations(controls)), "unanswered": len(unanswered(controls)),
            "na_pending": len(na_pending(controls)), "na_approved": len(na_approved(controls)),
            "not_required": len(not_required(controls)),
            "awaiting": len(awaiting_approval(controls)),
            "drafting": len(drafting(controls))}


def systems_for_role(inv, role, actor):
    if role == "governance":
        return inv
    col = "Business_Owner" if role == "business" else "Technical_Owner"
    return inv[inv[col] == actor].reset_index(drop=True)
