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
INV = os.path.join(HERE, "..", "01_inventory", "Synthetic_AI_System_Inventory.xlsx")
SYSMAP = os.path.join(HERE, "..", "04_ground_truth", "system_control_map.csv")
GOV = os.path.join(HERE, "..", "04_ground_truth", "control_evidence_map.csv")
ANSWERS = os.path.join(HERE, "..", "01_inventory", "owner_answers.json")
EXEMPTIONS = os.path.join(HERE, "..", "01_inventory", "exemption_claims.json")
STALE_DAYS = 180

ST_COMPLIANT = "Compliant"
ST_VIOLATION = "Violation"
ST_UNANSWERED = "Not answered"
ST_NA_PENDING = "N/A pending review"
ST_NA_APPROVED = "N/A approved"
ST_NOT_REQUIRED = "Response not required"


def load_inventory():
    df = pd.read_excel(INV, sheet_name="Inventory", header=3, engine="openpyxl")
    return df[df["SYS_ID"].notna()].reset_index(drop=True)


def load_sysmap():
    with open(SYSMAP, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_gov():
    with open(GOV, newline="", encoding="utf-8") as f:
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


# ---------------------------------------------------------------- compliance
def effective_value(row, attribute, answers):
    sid = row.get("SYS_ID")
    a = (answers.get(sid) or {}).get(attribute)
    if a and str(a.get("value", "")).strip():
        return str(a["value"]).strip(), True
    return "", False   # inventory value is a starting point only; see system_compliance


def audit_current(row):
    try:
        d = pd.to_datetime(row["Last_Audit_Date"]).date()
        return (dt.date.today() - d).days <= STALE_DAYS
    except Exception:
        return False


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


def system_compliance(row, sysmap, gov, g, answers=None, exemptions=None, role=None):
    answers = answers or {}
    exemptions = exemptions or {}
    sid = row.get("SYS_ID")
    ex_sys = exemptions.get(sid, {})
    cur = audit_current(row)
    out = []
    for rule in sysmap:
        if not applies(rule, row):
            continue
        if role and rule.get("owner_role") != role:
            continue
        cid, attr = rule["control_id"], rule["attribute"]
        req = required(rule, row)

        # owner answer wins; otherwise fall back to the inventory's recorded value
        if attr == "__audit_current__":
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


def not_required(controls):
    return [c for c in controls if c["status"] == ST_NOT_REQUIRED]


def compliant(controls):
    return [c for c in controls if c["status"] == ST_COMPLIANT]


def summarise(controls):
    return {"applicable": len(controls), "compliant": len(compliant(controls)),
            "violations": len(violations(controls)), "unanswered": len(unanswered(controls)),
            "na_pending": len(na_pending(controls)), "na_approved": len(na_approved(controls)),
            "not_required": len(not_required(controls))}


def systems_for_role(inv, role, actor):
    if role == "governance":
        return inv
    col = "Business_Owner" if role == "business" else "Technical_Owner"
    return inv[inv[col] == actor].reset_index(drop=True)
