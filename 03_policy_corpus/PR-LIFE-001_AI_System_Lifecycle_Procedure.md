# PR-LIFE-001 — AI System Lifecycle Procedure

- **Institution:** Meridian Financial Services (fictional, synthetic)
- **Document ID:** PR-LIFE-001 · Version 1.0
- **Owner:** Data Governance Department
- **Status:** Approved
- **RAG corpus layer:** Layer 2 — internal governance
- **Related Annex A controls (ISO/IEC 42001:2023):** A.6.1.3, A.6.2.2, A.6.2.3, A.6.2.4, A.6.2.5, A.6.2.6

> Synthetic content for academic demonstration.

## 1. Purpose
Defines the mandatory stages an AI system passes through from use-case definition to production, and the governance gates at each stage.

## 2. Lifecycle stages
2.1 **Registration.** Before development, the system is registered with a provisional record: system name/ID, purpose, expected data inputs, automated-decision flag, personal-data flag, and provisional risk level.

2.2 **Development.** The Technical Owner documents model design, training data references, and intended use. Registration attributes are completed as they become known.

2.3 **Verification and validation.** Prior to a go/no-go decision, the system undergoes validation against acceptance criteria (predictive performance, stability, and — where applicable — a documented human-oversight point). Validation results are recorded and attached to the go/no-go record.

2.4 **Deployment.** Deployment proceeds only after a go/no-go approval. The register status is updated to Active and the last-review date is set.

## 3. Human oversight in operation
3.1 For systems flagged as making or influencing automated decisions, the deployment record must state where a human can review, override, or halt the automated output. This oversight point is confirmed operational before go-live.

## 4. Review
4.1 Each system is re-validated at its defined review cadence. The register's last-review date is updated on each review. Systems whose last review predates the review window are treated as review-overdue and flagged for the Committee.
