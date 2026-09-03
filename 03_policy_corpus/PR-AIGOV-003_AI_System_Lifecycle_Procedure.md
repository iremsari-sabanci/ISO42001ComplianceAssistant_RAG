# PR-AIGOV-003 — AI System Lifecycle Procedure

- **Procedure owner:** AI Governance Team (Data Management and Analytics Directorate)
- **Status:** Published
- **Related Annex A controls:** A.6.1.2, A.6.1.3, A.6.2.2, A.6.2.3, A.6.2.4, A.6.2.5, A.6.2.6, A.6.2.7, A.6.2.8
- **RAG corpus layer:** Layer 2 — internal governance

## Purpose
Defines responsibilities, implementation steps, metrics and documentation requirements for all AI systems across their full lifecycle, from request intake to decommissioning.

## Scope and existing provisions
- Demand intake: AI requests are raised through the project/demand management application; the requesting unit states the business need, the problem, consequences of inaction, interface needs and business performance targets, which Analytics converts into technical metrics (precision, recall, F1, AUC).
- Scope, risk and impact analysis with opinions from Analytics (technical classification: RPA, agent, RAG, AI service, model development or third-party purchase), IT Infrastructure and Operations (hardware and capacity), Information Security (security posture, open-source risk) and Data Governance (personal data, customer and bank secret, autonomous decision authority, effect on sensitive groups).
- Development follows the software development lifecycle with AI-specific additions to the service design package: data provenance, data minimisation, performance and accuracy metrics; AI-specific ethical, representation and privacy risks added to risk scoring.
- Testing: machine-learning tests (generalisation, metric-based validation, adversarial robustness, data-leakage) and large-language-model tests (factuality, context adherence, direct and indirect prompt injection, jailbreak, bias).
- Independent validation by a party outside development, producing a validation report covering performance, bias analysis, explainability methods and a reasoned go-live opinion.
- Committee decision requires the service design package, the validation report and the AI impact assessment; incomplete submissions are returned without review.
- Deployment: infrastructure and rollback preparation, access and authorisation, transparency notices, event-log infrastructure, version control, and registration of the system in the AI System Inventory.
- Operation and monitoring: performance metrics, infrastructure and resource use, security threats and new asset-register risks are each monitored by the responsible directorate and reported to the Committee.
- Retirement: controlled decommissioning, notification of affected internal and external stakeholders within 30 days, archival under the retention and disposal policy, and a mandatory lessons-learned record signed by the business and technical owner directorates.

> **ACTION REQUIRED - PENDING ADDITION**
>
> This procedure does not yet contain the ISO/IEC 42001 provisions set out below. The addition must be drafted, approved and published by **AI Governance Team (Data Management and Analytics Directorate)** as the procedure owner. Until it is published, AI systems assessed against A.6.1.2, A.6.1.3, A.6.2.2, A.6.2.3, A.6.2.4, A.6.2.5, A.6.2.6, A.6.2.7, A.6.2.8 may show gaps that system owners cannot remediate themselves.


## Required ISO 42001 additions (not yet published)
- Periodic re-validation intervals by risk level. Validation is currently defined before go-live but no recurring interval is fixed afterwards.

The provisions above have been proposed by the AI Governance Team. They are **not yet part of this procedure**. **AI Governance Team (Data Management and Analytics Directorate)** is responsible for drafting, approving and publishing them; the AI Governance Team tracks closure but does not author other directorates' procedures.
