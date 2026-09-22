# Decision-Selection Worksheet

This worksheet reflects only the alternatives and analysis already documented in the architectural decision package. No new alternatives have been introduced, and no alternative has been selected.

---

## 1) Evidence classification

- Decision question: How should evidence status be represented and enforced at the event level?
- Available alternatives:
  - Explicit evidence classification in the event contract and provenance model
  - No formal event-level evidence classification or provenance contract
- Main advantages:
  - Provides a clear, explicit event-level record of raw input, derived output, and provenance chain.
  - Supports traceability and downstream assurance review.
- Main disadvantages:
  - Requires explicit contract and model changes.
  - Increases operational and governance overhead.
- Security implications:
  - Improves provenance clarity and auditability.
  - Reduces ambiguity in evidentiary disputes or tampering review.
- Operational implications:
  - Requires consistent tagging and validation across ingestion and normalization.
  - Increases implementation and QA complexity.
- Migration impact:
  - Existing event payloads and fixtures may need contract alignment.
  - Replay and validation workflows must account for evidence metadata.
- Recommendation criteria:
  - Determinism, auditability, provenance clarity, and fail-closed handling.
- Selected alternative: ______________________
- Rationale: ______________________

---

## 2) Source profile lifecycle and activation authority

- Decision question: Who is the authoritative owner of source profiles, and how are they activated and resolved?
- Available alternatives:
  - Platform Engineering-owned registry with explicit registration, versioned resolution, and fail-closed lookup
  - Ad hoc or implicit source resolution without formal lifecycle control
- Main advantages:
  - Makes source identity deterministic and replayable.
  - Prevents silent drift between parser, source context, and normalization output.
- Main disadvantages:
  - Requires registry governance and operational ownership.
  - Adds coordination and change-management overhead.
- Security implications:
  - Reduces risk of mismatched or untrusted source metadata.
  - Enforces explicit fail-closed behavior for unknown or malformed profiles.
- Operational implications:
  - Requires registry ownership, version control, and clear activation rules.
  - Any replay must resolve the exact original source profile version.
- Migration impact:
  - Need to standardize profile registration and version usage across runtime execution.
  - Existing implicit behavior must be replaced with explicit source resolution.
- Recommendation criteria:
  - Deterministic replay, authoritative ownership, fail-closed semantics, and schema conformance.
- Selected alternative: ______________________
- Rationale: ______________________

---

## 3) Ingestion boundary

- Decision question: Where should raw log intake occur, and what boundary must all ingestion respect?
- Available alternatives:
  - Formal public ingestion boundary using a raw log vault and explicit raw reference handling
  - Direct service-layer or demo-path ingestion that bypasses the formal boundary
- Main advantages:
  - Preserves raw payload integrity and provenance.
  - Keeps vaulting, hashing, and locator metadata centralized and consistent.
- Main disadvantages:
  - Requires disciplined use of the ingestion contract.
  - Bypasses or quick-path ingestion may create inconsistent data handling.
- Security implications:
  - Stronger provenance and evidence integrity.
  - Reduces risk of untracked or unverified raw log data entering the system.
- Operational implications:
  - Requires ingest contracts, raw locator metadata, and standardized validation.
  - Simplifies traceability and downstream replay.
- Migration impact:
  - Requires moving from demo/service direct reads to formal intake flow.
  - Any legacy bypass paths must be explicitly removed or isolated.
- Recommendation criteria:
  - Provenance preservation, formal boundary enforcement, and deterministic pipeline execution.
- Selected alternative: ______________________
- Rationale: ______________________

---

## 4) Durable raw storage and retention

- Decision question: What is the required persistence model for raw logs and how long should they be retained?
- Available alternatives:
  - Durable raw log vault with SHA-256 digests, locator metadata, and retention policy
  - Ephemeral or in-memory storage without durable retention enforcement
- Main advantages:
  - Enables auditability, replay, and trust in original raw payloads.
  - Supports tamper-evidence and later investigation.
- Main disadvantages:
  - Requires storage lifecycle management and operational retention controls.
  - Increases storage, cost, and governance requirements.
- Security implications:
  - Supports evidence preservation and legal/forensic review.
  - Reduces risk of losing raw source material needed for validation or disputes.
- Operational implications:
  - Requires retention policy, storage ownership, and cleanup procedures.
  - Must support access and retrieval through the approved public boundary.
- Migration impact:
  - Current in-memory or demo-only storage must be upgraded to a durable model.
  - Retention and access policies may require data migration or archival decisions.
- Recommendation criteria:
  - Evidence preservation, auditability, lifecycle clarity, and compliance fit.
- Selected alternative: ______________________
- Rationale: ______________________

---

## 5) Integrity and tamper-evidence

- Decision question: What integrity model must the system use to detect tampering and preserve trust in raw and derived artifacts?
- Available alternatives:
  - Cryptographic integrity model using SHA-256 payload digests, locator metadata, and a tamper-evident chain
  - No explicit tamper-evident chain or integrity model beyond ad hoc validation
- Main advantages:
  - Provides verifiable evidence of raw log integrity.
  - Protects replay and normalization from silent alteration.
- Main disadvantages:
  - Requires chain management and careful operational handling.
  - Adds implementation and validation complexity.
- Security implications:
  - Improves detection of tampering and unauthorized modifications.
  - Supports chain-of-custody and audit review requirements.
- Operational implications:
  - Requires consistent hashing, verification, and troubleshooting procedures.
  - Should be paired with explicit failure semantics on integrity mismatch.
- Migration impact:
  - Current raw storage and event contract may require integrity metadata additions.
  - Validation workflows must reject previously unverifiable records.
- Recommendation criteria:
  - Tamper detection, reproducibility, provenance, and fail-closed handling.
- Selected alternative: ______________________
- Rationale: ______________________

---

## 6) Governance enforcement

- Decision question: What enforcement model is required to keep parser, source profile, and runtime behavior authoritative and fail-closed?
- Available alternatives:
  - Governance enforced through explicit registry API, validation, and fail-closed semantics
  - Permissive runtime behavior with no formal governance enforcement
- Main advantages:
  - Prevents drift, ambiguity, and silent rule bypass.
  - Aligns ownership and accountability with operational responsibilities.
- Main disadvantages:
  - Requires registry policy, enforcement logic, and operational discipline.
  - Can slow down non-standard or ad hoc changes unless governed properly.
- Security implications:
  - Reduces unauthorized profile or parser activation.
  - Supports deterministic, audit-friendly execution.
- Operational implications:
  - Requires explicit ownership, version discipline, and public API enforcement.
  - Failures become explicit rather than hidden.
- Migration impact:
  - Existing bypass or implicit pathways must be converted to governed access patterns.
  - Validation and replay must respect the governance contract.
- Recommendation criteria:
  - Determinism, explicit ownership, fail-closed behavior, and policy consistency.
- Selected alternative: ______________________
- Rationale: ______________________

---

## Team decision capture

- Selected alternative for each decision: ______________________
- Rationale for each decision: ______________________

This worksheet is ready for team selection.
