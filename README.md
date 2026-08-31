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

## Impact assessment & human oversight (update)

**A.5.2 impact assessment — asked for every system.** ISO 42001 places no attribute-based
restriction on impact assessment, so the question is now shown to the business owner of
every system (previously filtered to automated-or-personal-data systems). The **AI
Governance Team** evaluates whether an assessment is necessary and how detailed it must
be; that determination is recorded through the exemption/review path (`exemption_allowed=Y`),
so the decision is documented rather than silently encoded in a trigger.

**A.9.3 human oversight — shown always, required conditionally.** Necessity of human
oversight is an organizational determination, not a fixed rule. The question is therefore
displayed for every system, but a response is only **required** where the system makes
automated decisions. Where it is not required, the intake screen explains why and the
answer is optional; the control shows as **Response not required** and counts neither as
compliant nor as a violation.

Answer vocabulary now reflects oversight modes: **human-in-the-loop / human-on-the-loop /
none**. Either loop mode satisfies the control (`compliant_if` supports several acceptable
values); `none` on an automated-decision system is a violation.

New columns in `system_control_map.csv`: `required_when` (when an answer is mandatory —
distinct from `applies_when`, which controls display) and `not_required_note` (the
on-screen explanation). New status: **Response not required**, with its own metric in the
compliance view and Portfolio.

Effect: AML monitoring and Loan Default Early Warning (non-automated, human-reviewed) now
surface their **human-on-the-loop** oversight instead of being silently skipped, and
automated systems recording `none` (Marketing Optimizer, Collections, HR CV Screening) are
correctly flagged as violations.

## Update: answer/claim conflict, A.5.2, and the Procedure Owner role

**1. An answer and an N/A claim can no longer coexist.** Submitting an N/A claim clears any
recorded answer; while an answer exists the claim path is hidden with a note to clear it
first; and owners can now undo an accidental selection with **Clear my answer**. A control
therefore always has exactly one state.

**2. A.5.2 impact assessment is no longer claimable as not-applicable.** Clause 8.4 requires
the organization to perform AI system impact assessments per 6.1.4 at planned intervals or on
significant change - unconditional for in-scope AI systems. B.5.2's "conditions" govern when
an assessment is triggered and how detailed it is, not whether a system may be excluded. It is
asked of every system; the AI Governance Team still sets depth. Claimable controls are now
A.6.2.4, A.6.2.8, A.7.4, A.8.2, A.8.4, A.9.3.

**3. New role: Procedure owner (policy/procedure).** Governance readiness is now a working
queue, not a read-only list:
- The **AI Governance Team** assigns each Annex A policy gap to a responsible department,
  with an instruction (new procedure, or addition to an existing one?) and a due date.
- The **Procedure owner** signs in by department, sees only the gaps assigned to them, and
  records status (Open / In progress / Drafted - in review / Completed), what was added, and
  the resulting document reference.
- Governance sees the owner's update and document reference back in the readiness view, with
  an "assigned" count alongside the gap count.

State persists to `01_inventory/policy_actions.json`; departments and statuses are defined in
`core.PROCEDURE_OWNERS` / `core.POLICY_ACTION_STATUS`.

## Inventory and stakeholders (update)

The inventory is now **English and adapted from an institutional AI system inventory**
(`01_inventory/AI_System_Inventory.xlsx`, 22 systems, 22 data sources). It is
de-identified: no institution name, generalised unit names, use-case level descriptions,
illustrative compliance attestations. See `DATA_SOURCES.md` for the references section.

Systems span fraud scoring (card / ATM / transfer), collections prediction, credit-card
limit prediction, identity-photo blacklist matching, special-category field redaction,
churn and product-propensity models, behavioural segmentation, survey and complaint text
classification, cheque and instruction signature verification, identity/trade/mortgage/KEP
document extraction, a pricing model still in development, and a shared OCR platform
service.

**Procedure stakeholders** (`core.PROCEDURE_OWNERS`): AI Governance Team, Artificial
Intelligence Solutions Directorate, Data Management and Analytics Directorate, IT
Infrastructure and Operations Directorate, Information Security Directorate, IT Strategy
and Governance Directorate.

**`04_ground_truth/procedure_responsibility_map.csv`** answers "which procedures should we
have, and who owns them": for all 38 Annex A controls it names the proposed procedure, the
recommended primary and contributing directorate, and whether it is a **new** procedure
(24) or an **addition** to an existing one (14). The Governance readiness tab shows this
and pre-fills the assignment dropdown with the recommended owner.


## Inventory update — blended and expanded (39 systems)

The inventory now **blends** entries adapted and de-identified from an institutional AI
service inventory with additional **synthetic** entries created for this project. The two
are deliberately not distinguished, so no individual row can be attributed to the
organisation. Unit names are generalised, descriptions are written at use-case level, and
attestations, review dates, stewardship and data-quality tags are illustrative.

39 systems across 21 business units and 6 AI Solutions teams, 33 data sources, 103 lineage
edges. Coverage: fraud scoring (card / ATM / digital channel), retail credit scoring, credit
card limit prediction, AML transaction monitoring, cross-region ATM anomaly detection,
collections prediction, loan default early warning, identity-photo watchlist matching,
special-category field redaction, churn / propensity / segmentation / campaign optimisation,
survey and complaint text classification, call-centre speech analytics, a multilingual
virtual assistant, cheque and instruction signature verification, identity / cheque / note /
instruction / trade / KEP / mortgage document extraction, financial-statement digitisation,
contract text template matching, two pricing models, corporate media intelligence, QR and OCR
platform services, branch cash forecasting and CV screening support.

**Scope note.** Scheduled SQL reports and rule-based extracts that involve no AI technique
are excluded from the inventory; they should be scoped out of the AIMS by formal decision
rather than assessed against Annex A.

**Naming.** The governance role is now
*AI Governance Team (Data Management and Analytics Directorate)*, reflecting its parent
directorate, in `core.PROCEDURE_OWNERS` and in the procedure responsibility map.


## Inventory rebalanced + intended-use authoring workflow

**Simple detection services trimmed.** Presence/absence style services were removed and
only one is retained (Cheque Signature Presence Detection) as a representative case;
redundant single-document extraction services were also dropped. Data stewardship and
lineage obligations carry little meaning for a service that only answers "is a signature
present?", so the portfolio now weights toward systems where governance is substantive.

**Nine complex services added** (44 systems total, 39 data sources): Voice Biometrics
Authentication, Robo-Advisory Portfolio Recommendation, Credit Memo Generative
Summarisation (LLM), Internal Knowledge Assistant (retrieval-augmented, cited sources),
Real-Time Transaction Categorisation, Customer Lifetime Value Prediction, Insider Risk
Behaviour Analytics, Model Drift Monitoring Platform, and a Synthetic Data Generation
Service. These introduce biometric data, generative AI, employee personal data and
model-lifecycle telemetry - areas where stewardship, lineage and oversight genuinely apply.

**A.9.4 intended use is now an authored document, not a Y/N flag.** The business owner
writes and edits the intended-use statement in the app (purpose, users, decisions
supported, prohibited uses) and submits it; the AI Governance Team adds its own section -
scope limits, prohibited uses, oversight conditions - and approves or returns it with a
note. Statuses: `Not answered` -> `Draft in progress` -> `Awaiting governance approval` ->
`Compliant` (or `Returned`). Only approval makes the control compliant, so the record
carries both parties' input and an approval trail. Systems already marked as documented in
the inventory are honoured as legacy-approved. State persists to
`01_inventory/intended_use.json`.


## Intended-use register (AI Governance Team)

The governance tab is now **"Approvals & intended use"** and has two parts:

1. **Awaiting approval** - statements the business owner has submitted; the Governance Team
   adds its section and approves or returns them.
2. **Intended-use register - all systems** - every system with its state (approved /
   awaiting / draft / returned / not started), owner, risk, approver and a statement
   preview, plus counters and a picker to read any full statement together with the
   Governance Team's addition.

The **Portfolio** tab also carries an *Intended use* column, so the state is visible
alongside violations for the whole estate.

Note: systems whose inventory record carried `Intended_Use_Doc = Y` display as
**"approved (legacy record)"** - the flag is honoured but no statement text or approver
exists. Treat these as a backlog to re-document through the workflow.


## Intended use (A.9.4): Yes/No + document, and a governance completeness block

Approval of content was **replaced by completeness validation**. ISO 42001 does not require
the AI Governance Team to approve an intended-use document, but several fields are
organizational determinations that a system owner cannot self-assert.

**Business owner** answers *Is there an intended-use document for this system?*
- **Yes** -> a **document reference is required** (ID, DMS link or version). A bare "Yes"
  is rejected, so the tick is always evidenced.
- **No** -> the in-app template opens with 10 headings; 5 are required (purpose and
  rationale, intended users, intended use, scope of application, limitations). The others:
  data used, technical assumptions, human oversight in practice, monitoring and review
  triggers, related records. System identification comes from the inventory and is not
  re-keyed.

**AI Governance Team** does not approve the prose but must complete five fields:
risk classification; whether an impact assessment is required; its depth (B.5.2 conditions);
the human-oversight determination (necessary? in-the-loop / on-the-loop / not required, per
B.9.3); and policy-level prohibited uses.

**A.9.4 is compliant only when a document exists AND the governance block is complete.**
States: `Not answered` -> `Document in progress` -> `Governance block incomplete` ->
`Compliant`. Systems carrying the old inventory flag now show `legacy` and appear in the
governance-block queue rather than passing silently.

The governance tab lists systems with the block outstanding, the full register with
counters, and a reader for any document plus its governance block.


## A.6.2.6 made actionable + Risk & compliance AI is now a chat

**A.6.2.6 (operational review) was visible but unfixable.** It is derived from
`Last_Audit_Date`, so it appeared as a violation with no question behind it. The intake tab
now renders it: the owner sees the last review date, how many days have passed against the
180-day window, and any recorded note, and can **record a review** with a date and a short
description of what was reviewed. The effective review date is the later of the inventory
date and any recorded review, so recording one clears the violation. History is kept
(last 10 entries) in `01_inventory/system_reviews.json`. Governance sees the state but
owners record their own reviews.

**The remediation tab is now "Risk & compliance AI (chat)".** It is a grounded Q&A chat
over the selected system: the owner asks questions ("what does A.7.5 require?", "how do I
fix my data quality gap?", "what are my violations?") and the assistant answers from that
system's control statuses, control intent and governing procedures. Conversation history is
kept per system and role, the "Draft a remediation plan" action is still available as a
starter, each answer shows backend, model and prompt/completion token counts, and the
retrieved grounding context is inspectable in an expander. The transcript can be downloaded.

With no LLM configured the chat degrades to **retrieval-only**: it returns the controls
matching the question, and says plainly when the question falls outside this system's
control set rather than inventing an answer.


## Operational review (A.6.2.6) is now a structured, joint review

"What was reviewed" was free text, which invites "checked, fine" - useless as evidence.
It is now a **role-split checklist with a required outcome**, derived from B.6.2.6
(system and performance monitoring, repairs, updates, support).

**Business owner confirms:** still used for its documented intended purpose with no
unforeseen use; scope reviewed (segments, products, channels, geographies); concerns,
complaints and user feedback reviewed; human oversight operating as defined and override
frequency reviewed; regulatory, contractual or policy changes considered; use case still
needed and delivering its benefit.

**Technical owner confirms:** performance against acceptance criteria (error rates,
confidence, stability on production data); data and concept drift, and whether retraining
is indicated; errors, failures and incidents with repairs; updates and model versions
released and users informed; event logging still enabled and complete; AI-specific security
threats reviewed (data poisoning, model theft, model inversion).

Each side must tick every item and select an **outcome** - Continue unchanged / Remediate -
actions raised / Revalidate / New impact assessment required / Refer for retirement - plus
free-text findings.

**The review counts only when both sides are complete**, and the effective review date is
the earlier of the two, so one party cannot sign off alone and a partial checklist does not
count. Until then the inventory date remains the basis. Both sides' status, outcome and
notes are shown on the control, and the last 20 entries are retained as history in
`01_inventory/system_reviews.json`.

## Policy corpus built from the real procedure set

`03_policy_corpus/` now holds **29 documents** covering the actual AIMS document set, one
per procedure, owned by the responsible directorate: AI Governance Team (AI Policy,
Committee Procedure, **AI System Lifecycle Procedure**, Impact Assessment Procedure), Data
Governance Service (8), IT Strategy and Governance (6), IT Infrastructure and Operations
(6), Information Security (3), Human Resources (1) and AI Solutions (1).

Each document states its owner, status and Annex A controls. Where an ISO 42001 addition
has been proposed but not published, the document carries an **ACTION REQUIRED - PENDING
ADDITION** warning naming the department that must draft, approve and publish it, and
stating that the AI Governance Team tracks closure but does not author other directorates'
procedures. Status split: 4 published, 21 published-with-addition-pending, 4 not yet
created. The evidence and responsibility maps were realigned to these real procedure names
(14 controls evidenced, 24 gaps).

**Procedure update requests.** The AI Governance Team can now raise free-form requests from
its own page - procedure owner, procedure, section, requested addition, related control and
due date - for additions not tied to a specific Annex A gap. The request appears on that
directorate's page, where they set a status (Open / Acknowledged / In progress / Drafted -
in review / Published / Declined) and record what they added. Governance sees every request
and its response in a table. State persists to `01_inventory/procedure_requests.json`.

Naming: the Human Resources Directorate is used throughout, and the project/demand
management application is referred to generically rather than by product name.

## Language

The class is taught in English, so every academic-facing artifact is in English: the
29-document policy corpus, the 44-system inventory workbook, the Annex A knowledge graph,
the ground-truth maps, the application UI and all generated reports.

`04_ground_truth/Procedure_Update_Proposals_EN.xlsx` is the English-only version of the
procedure update proposals (27 rows: 8 endorsed existing proposals, 19 new suggestions),
with procedure names, section headings and owning directorates translated.

The bilingual Turkish/English version has been moved to `05_institutional/`, which is
excluded from the academic deliverable and from the RAG corpus - it exists for the
procedure owners who must draft and publish the additions.

The only Turkish text remaining outside that folder is two proper nouns that should not be
translated: **Türk Standardları Enstitüsü** (the standards body cited in the references)
and **VERBİS** (the data protection registry).

## System descriptions for governance decisions

The AI Governance Team cannot judge an exemption claim or a violation without knowing what
the system actually does, so the description now appears wherever a decision is made:

- **System summary panel** — an expander directly under the title, visible on every tab as
  soon as a system is selected: what it does, risk level, automated-decision and
  personal-data flags, environment, business and technical owner, data steward and status,
  data inputs, lineage, data-quality regime and last review date.
- **Portfolio** — a "What it does" column beside the system name, so the whole estate can
  be scanned without opening each system.
- **Exemption reviews** — each pending claim now shows what the system does, its risk level
  and its automated-decision and personal-data flags above the owner's justification, so
  the claim is judged in context.
- **Intended-use register** — a "What it does" column, so a statement can be assessed
  against the system's actual purpose.

The compliance tab no longer repeats these details; it points to the summary panel.
