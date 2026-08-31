# PR-DG-004 — RAG and Corporate Document Corpus Standard

- **Procedure owner:** Data Governance Service (Data Management and Analytics Directorate)
- **Status:** Not yet created - required by ISO 42001
- **Related Annex A controls:** A.7.2, A.7.3
- **RAG corpus layer:** Layer 2 — internal governance

## Purpose
Governs document corpora used by retrieval-augmented generation services.

> **ACTION REQUIRED - PENDING ADDITION**
>
> This procedure does not yet contain the ISO/IEC 42001 provisions set out below. The addition must be drafted, approved and published by **Data Governance Service (Data Management and Analytics Directorate)** as the procedure owner. Until it is published, AI systems assessed against A.7.2, A.7.3 may show gaps that system owners cannot remediate themselves.


## Required ISO 42001 additions (not yet published)
- Which documents may be ingested into a corpus and who approves ingestion.
- Inheritance of source access rights into the vector store, so retrieval cannot surface a document to a user who could not open it directly.
- Re-indexing when a document is revised, superseded or retired.
- Prohibition of customer secret and bank secret content in prompts sent outside the on-premises boundary.

The provisions above have been proposed by the AI Governance Team. They are **not yet part of this procedure**. **Data Governance Service (Data Management and Analytics Directorate)** is responsible for drafting, approving and publishing them; the AI Governance Team tracks closure but does not author other directorates' procedures.
