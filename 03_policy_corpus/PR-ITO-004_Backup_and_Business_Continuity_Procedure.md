# PR-ITO-004 — Backup and Business Continuity Procedure

- **Procedure owner:** IT Infrastructure and Operations Directorate
- **Status:** Published - ISO 42001 addition pending
- **Related Annex A controls:** A.4.5
- **RAG corpus layer:** Layer 2 — internal governance

## Purpose
Defines backup, restoration and continuity for production services.

## Scope and existing provisions
- Backup scope and schedules, recovery objectives and continuity testing.

> **ACTION REQUIRED - PENDING ADDITION**
>
> This procedure does not yet contain the ISO/IEC 42001 provisions set out below. The addition must be drafted, approved and published by **IT Infrastructure and Operations Directorate** as the procedure owner. Until it is published, AI systems assessed against A.4.5 may show gaps that system owners cannot remediate themselves.


## Required ISO 42001 additions (not yet published)
- AI assets brought into backup and disaster recovery scope: model artefacts and weights, feature stores, vector indexes and retrieval corpora.
- Recovery time and recovery point objectives defined per AI service.
- Model reload and index rebuild included in disaster recovery tests; a restored application without its model or index is not a restored service.

The provisions above have been proposed by the AI Governance Team. They are **not yet part of this procedure**. **IT Infrastructure and Operations Directorate** is responsible for drafting, approving and publishing them; the AI Governance Team tracks closure but does not author other directorates' procedures.
