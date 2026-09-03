# PR-ITO-002 — Change Management Procedure

- **Procedure owner:** IT Infrastructure and Operations Directorate
- **Status:** Published - ISO 42001 addition pending
- **Related Annex A controls:** A.6.2.5
- **RAG corpus layer:** Layer 2 — internal governance

## Purpose
Governs changes to production systems.

## Scope and existing provisions
- Change types, approval, scheduling, implementation and post-implementation review.

> **ACTION REQUIRED - PENDING ADDITION**
>
> This procedure does not yet contain the ISO/IEC 42001 provisions set out below. The addition must be drafted, approved and published by **IT Infrastructure and Operations Directorate** as the procedure owner. Until it is published, AI systems assessed against A.6.2.5 may show gaps that system owners cannot remediate themselves.


## Required ISO 42001 additions (not yet published)
- Model deployment and retraining defined as a distinct change type; a retrained model is a change even when no code changes.
- Model version and artefact hash recorded on the change record.
- A tested rollback to the last stable version required before approval.
- Canary or shadow deployment for high-risk systems.

The provisions above have been proposed by the AI Governance Team. They are **not yet part of this procedure**. **IT Infrastructure and Operations Directorate** is responsible for drafting, approving and publishing them; the AI Governance Team tracks closure but does not author other directorates' procedures.
