# PR-SEC-002 — Log Management Procedure

- **Procedure owner:** Information Security Directorate
- **Status:** Published - ISO 42001 addition pending
- **Related Annex A controls:** A.6.2.8
- **RAG corpus layer:** Layer 2 — internal governance

## Purpose
Defines log generation, collection, protection and retention.

## Scope and existing provisions
- Log sources, pipeline configuration, protection against tampering and retention periods.

> **ACTION REQUIRED - PENDING ADDITION**
>
> This procedure does not yet contain the ISO/IEC 42001 provisions set out below. The addition must be drafted, approved and published by **Information Security Directorate** as the procedure owner. Until it is published, AI systems assessed against A.6.2.8 may show gaps that system owners cannot remediate themselves.


## Required ISO 42001 additions (not yet published)
- AI-specific log fields defined as a standard: timestamp, system and model version, input reference (hashed), output or decision, confidence score, human override events, and for LLM services the prompt and response identifiers.
- Log pipeline configuration requirements for the platforms on which models run.
- Retention aligned with the personal data rules and the audit-trail need; logging of raw special-category data prohibited.

The provisions above have been proposed by the AI Governance Team. They are **not yet part of this procedure**. **Information Security Directorate** is responsible for drafting, approving and publishing them; the AI Governance Team tracks closure but does not author other directorates' procedures.
