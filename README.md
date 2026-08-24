# Synthetic dataset — ISO 42001 Compliance Assistant (DA592)

A fully fabricated stand-in for the confidential institutional data, so the academic
project can be built, evaluated, and presented without disclosing any real bank
information. The **same pipeline runs on this synthetic data (for school) and on the
real inventory (inside the institution, never leaving)**.

Fictional institution throughout: **Meridian Financial Services**. No real institution,
system, dataset, or individual is represented.

## Contents

```
01_inventory/
  Synthetic_AI_System_Inventory.xlsx   5 sheets: Inventory · Data_Sources ·
                                        Lineage_Edges · Gap_Summary (live formulas) ·
                                        Data_Dictionary. 12 systems, Layer 5 source.
02_knowledge_graph/
  iso42001_annexA_nodes.csv            38 Annex A control nodes (real structure)
  iso42001_annexA_edges.csv            22 typed edges (requires / mitigates / extends)
  iso42001_annexA_kg.jsonld            portable JSON-LD export
  build_kg_networkx.py                 loads the graph; demos BFS augmentation + trigger filter
03_policy_corpus/
  POL-AIGOV-001 … PR-MON-001 (5 .md)   Layer 2 corpus; some controls covered, some omitted
04_ground_truth/
  control_evidence_map.csv             all 38 controls: evidence present vs. gap
README.md
```

## Knowledge graph — now built from the real standard
The knowledge graph is reconciled against ISO/IEC 42001:2023 Annex A: the full
**38 controls** in their nine objective groups (A.2–A.10), with the standard's
canonical control IDs and titles. Each node carries an **original one-line paraphrase**
(`clause_summary`) written from scratch — the standard's control-requirement text and
Annex B guidance are **not** reproduced. `clause_text_verbatim` is left blank for you to
populate from your licensed copy. Dependency edges (`requires` / `mitigates` / `extends`)
are an interpretation of how controls relate, not a structure defined by the standard;
review them before relying on them.

## How the pieces line up
- The inventory is the **Layer 5** knowledge source; the policy corpus is **Layer 2**.
- Per-system gaps (lineage / data-quality / stewardship / stale audit) are computed live
  in `Gap_Summary`. Control-level evidence vs. gaps are in `control_evidence_map.csv`
  (21 controls evidenced, 17 gaps across the corpus).
- The corpus deliberately omits transparency-to-users (A.8.2, A.8.5), external reporting
  (A.8.3), societal-impact assessment (A.5.5), responsible-use processes (A.9.2, A.9.4),
  fairness/bias monitoring (A.9.3 is principle-level only), and third-party controls
  (A.10.2–A.10.4). So the proposal's showcase query — *"which of our AI systems have gaps
  in bias monitoring?"* — returns a real, defensible A.9.3 gap for the automated /
  high-risk systems.
- `control_evidence_map.csv` doubles as the **answer key** for your 50–80-pair governance
  Q&A benchmark (Deliverable 4): control-mapping, gap-detection, evidence-retrieval.

## DAMA tags → real Annex A data controls
- Lineage_Status  → **A.7.5** Data provenance
- DQ_Regime       → **A.7.4** Quality of data for AI systems
- Steward_Status  → **A.3.2** roles / **A.7.2** data-management processes

## Correction note (important for your proposal)
The control IDs in the earlier draft proposal and PR-DEP-003 do not match Annex A:
- **A.5** is *Assessing impacts of AI systems* (impact assessment) — not an "AI system
  register". The AI inventory is not an Annex A control; it is SoA scope / operational.
- **A.6.2** is the *AI system life cycle* objective group — not "risk management". Risk
  management lives in **Clauses 6.1.2 / 6.1.3 / 8.2 / 8.3** (main requirements), not Annex A.
- **Data quality** is **A.7.4** (not A.8.4). **A.8.4** is *Communication of incidents*.
- **Data provenance / lineage** is **A.7.5** (not A.8.2). **A.8.2** is *System documentation
  and information for users*.
- **Human oversight** is not a standalone numbered control; it sits inside **A.9.3**
  (objectives for responsible use) and its guidance (B.9.3), not "A.10.1".

Update the proposal's example edges accordingly (e.g. A.6.2.4 verification → requires →
A.7.4 data quality; A.9.3 responsible-use → extends → A.6.1.2 development objectives).

## Full UI: compliance_app.py
`02_knowledge_graph/compliance_app.py` connects all four layers. Run it from that
folder with `streamlit run compliance_app.py` (needs `streamlit pandas openpyxl networkx`).
Three tabs: **System coverage** (pick a system from the inventory → applicable controls
with evidence/gaps), **Evidence explorer** (pick a control → see the ground-truth mapping
and open the actual policy-corpus document behind it), and **Portfolio** (control gaps +
data gaps across all 12 systems).

## Generation — the "G" in RAG: generation.py + Gap report tab
`generation.py` turns the retrieved controls + policy evidence into a written
clause-level gap report. The backend is pluggable via the `LLM_BACKEND` env var:
`template` (default, no LLM, 0 tokens), `ollama`, `openai` (any OpenAI-compatible
server incl. vLLM/LM Studio, or hosted), or `transformers` (local HF pipeline on
the H200). It falls back to the template if the chosen backend is unavailable.
The app's fourth tab, "Gap report (RAG generation)", generates the report, shows
prompt (input) and completion (output) token counts, and reveals the exact prompt
sent to the model — so you can see where the LLM tokens are spent.

Examples (from the 02_knowledge_graph folder):
    # on-prem, local Ollama
    set LLM_BACKEND=ollama & set OLLAMA_MODEL=llama3.1 & streamlit run compliance_app.py
    # any OpenAI-compatible server (e.g. local vLLM)
    set LLM_BACKEND=openai & set OPENAI_BASE_URL=http://localhost:8000/v1 & set LLM_MODEL=... & streamlit run compliance_app.py

---

## MODEL UPDATE — per-system compliance (supersedes the corpus-gap version)

The assistant now answers the correct question: **given our established ISO 42001
policies (assumed complete), which AI systems violate them?** Compliance is judged
**per system, from that system's own inventory record** — not from gaps in the policy
corpus (which was identical for every system and belonged elsewhere).

- The inventory gained per-system **control attestations** (Impact_Assessment,
  Human_Oversight, Verification_Validation, Technical_Doc, Event_Logging,
  Incident_Plan, User_Transparency, Intended_Use_Doc), joining the existing
  lineage / data-quality / steward / audit-date signals.
- `04_ground_truth/system_control_map.csv` maps each attestation to an Annex A control,
  its applicability trigger, and the value required for compliance.
- `compliance_app.py` tabs: **System compliance** (per-system violations + owner alert),
  **Fix with AI** (per-system LLM remediation for that system's violations),
  **Portfolio** (which services are non-compliant), and **Governance readiness (org)** —
  the policy-set completeness view, assessed once org-wide, deliberately NOT per system.
- `generation.py` now writes **per-system remediation** addressed to the business and
  technical owners: for each violation, how to fix it and which inventory field to update.

Well-governed systems (e.g. Credit Scoring, Fraud, KYC OCR, Loan Default) show 0
violations; poorly-governed ones (e.g. HR CV Screening) show many — real per-system
differentiation. The goal: owners act on their system's alerts, update the inventory,
and the system flags non-compliance automatically.

## Role-based workflow (owner-driven intake)

Sign in from the sidebar as **Business owner**, **Technical owner**, or **AI Governance
Team**. Owners see only the systems where they are named owner; the Governance Team sees
all.

- **Questions (intake)** — the assistant asks that role's questions for the selected
  system. Answers persist to `01_inventory/owner_answers.json` (the .xlsx stays
  pristine) and immediately re-evaluate compliance. Business owners are asked about
  impact assessment, stewardship, oversight, transparency, incident plan, intended use;
  technical owners about V&V, technical documentation, logging, data quality, lineage.
- **My compliance** — that system's violations for this role, with owner alerts.
- **Risk & remediation (AI)** — per-system LLM feedback for the selected system.
- **Portfolio** — *AI Governance Team only*: all systems, violation counts, and
  intake progress ("owner answers received").
- **Governance readiness** — *AI Governance Team only*: org-level policy completeness.

`core.py` holds the shared compliance rules and answer persistence so an agent/batch job
can reuse them outside the UI.

## Adjudicated exemptions + control scope (update)

**"Not applicable" is now a claim, not an answer.** Previously any value other than the
compliant one - including "n/a" - counted as a violation, penalising systems for controls
that did not apply and rewarding owners who answered "Y" to everything.

Five statuses; only **Violation** counts against a system:
- `Compliant`, `Violation`
- `Not answered` - intake gap, distinct from a "No"
- `N/A pending review` - owner claimed not-applicable **with a required justification**;
  counted as neither compliant nor violating
- `N/A approved` - AI Governance Team accepted the claim; excluded from scoring, with the
  justification, approver and timestamp retained (a per-system Statement-of-Applicability trail)

Workflow: owner answers Y/N, or opens "This control does not apply to my system", writes a
justification and submits -> the claim appears in the Governance Team's **Exemption reviews**
tab -> Approve (excluded) or Reject (reverts to Violation, owner alerted). `exemption_allowed`
in `system_control_map.csv` limits which controls may be claimed at all; the automatic
`applies_when` triggers still filter structurally inapplicable controls before they are asked.
The Portfolio view shows N/A pending and approved counts so a green score cannot be
manufactured by claiming exemptions.

**A.8.4 reclassified.** Incident communication is an *organizational* capability - Annex B.8.4
allows AI incident response to be integrated into wider organizational incident management,
with awareness of AI/PII-specific reporting duties. It is no longer asked as "does this system
have an incident plan"; the per-system question is now whether *this system's users and
AI-specific incident scenarios are covered by the organizational plan*. `system_control_map.csv`
now carries a `scope` column (`system` vs `org_instance`) and a `per_system_justification` for
every control, surfaced in the Governance readiness tab - use it for the methodology section.
