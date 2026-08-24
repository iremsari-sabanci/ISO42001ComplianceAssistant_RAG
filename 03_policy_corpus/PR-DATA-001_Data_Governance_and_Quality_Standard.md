# PR-DATA-001 — Data Governance & Quality Standard for AI

- **Institution:** Meridian Financial Services (fictional, synthetic)
- **Document ID:** PR-DATA-001 · Version 1.0
- **Owner:** Data Management & Analytics
- **Status:** Approved
- **RAG corpus layer:** Layer 2 / Layer 3 — data governance reference
- **Related Annex A controls (ISO/IEC 42001:2023):** A.4.3, A.7.2, A.7.4 (data quality), A.7.5 (data provenance)

> Synthetic content for academic demonstration. Vocabulary is informed by DAMA-DMBOK
> knowledge areas (Metadata Management, Data Quality, Data Governance).

## 1. Purpose
Establishes how data resources feeding AI systems are documented, how lineage is recorded, and how data quality is evidenced.

## 2. Data resources
2.1 Each data source feeding an AI system is registered with an identifier, type, ownership, and a personal-data flag. Sources are listed against the systems they feed.

## 3. Data lineage (Metadata Management)
3.1 Lineage is recorded structurally as source → system → consumer. Lineage completeness is tagged per system as complete, partial, or absent.

3.2 An absent or partial lineage record is itself a reportable finding; it does not block registration but is surfaced to governance for remediation.

## 4. Data quality (Data Quality)
4.1 Each source is tagged for the presence or absence of a data-quality regime. Where a regime is present, quality is monitored against agreed expectations for the source.

4.2 The absence of a data-quality regime for a source feeding a Medium- or High-risk system is recorded as a data-quality gap.

## 5. Stewardship (Data Governance)
5.1 Stewardship status is recorded per system as assigned, de facto, or unassigned. An unassigned steward is recorded as a governance gap.
