# Approved Decision Record (ULPF)

## Document status
- Status: Approved
- Scope: Architectural decisions for the ULPF project
- Constraint: No implementation work has been authorized by this record.

## Approved architectural direction

This record approves the following architectural directions for the project:

1. Evidence classification: explicit event-level evidence classification and provenance semantics.
2. Source profile lifecycle and activation authority: governed, versioned registry with explicit activation and fail-closed lookup.
3. Ingestion boundary: formal public ingestion boundary using the raw vault and explicit raw reference handling.
4. Durable raw storage and retention: durable raw log vault with SHA-256 digests, locator metadata, and retention policy.
5. Integrity and tamper-evidence: SHA-256 payload digests with a tamper-evident chain.
6. Governance enforcement: registry API enforcement, validation, and fail-closed runtime behavior.

---

## 1) Evidence classification

### Selected alternative
- Explicit event-level evidence classification and provenance semantics.

### Decision summary
The project will represent evidence status explicitly at the event level, with provenance semantics that make the origin, derivation, and evidentiary status of data clear and auditable.

### Scope boundary
- Applies to event model, provenance metadata, and downstream evidence handling.
- Includes source traceability and any future validation or investigative workflows.

### Technical rationale
- The repository design documents consistently distinguish raw inputs, derived outputs, and authoritative source context.
- The event contract already includes provenance-oriented fields such as raw references and metadata that imply a traceable event envelope.
- Explicit evidence semantics reduce ambiguity in replay, audit, and forensic review.

### Business rationale
- Makes evidence traceability understandable to security, operations, and compliance stakeholders.
- Supports defensible handling of enterprise log provenance and incident review.

### Operational rationale
- Creates a consistent operational expectation for how log lineage, raw references, and evidence status are represented.
- Improves reliability of investigations and downstream validation.

### Rejected alternatives and reasons
- No formal event-level evidence classification or provenance contract.
  - Rejected because it leaves evidence status ambiguous and weakens auditability and determinism.

### Required contract changes
- Event contract updates to represent evidence classification explicitly.
- Provenance and raw-reference semantics must be formalized and consistently documented.
- Any event-level evidence model must remain compatible with the existing event envelope contract.

### Required implementation changes
- Add explicit evidence classification fields and provenance semantics in the event model.
- Ensure all ingestion and normalization paths populate evidence metadata consistently.
- Enforce validation on evidence metadata where appropriate.

### Migration implications
- Existing payloads and references may need to be upgraded or normalized to the new evidence contract.
- Historical or demo data may require migration or explicit non-binding treatment.

### Security implications
- Improves forensic and operational trust in event lineage.
- Clarifies restrictions on how raw and derived evidence are represented or relied upon.

### Test acceptance criteria
- Event payloads include the required evidence metadata.
- Unknown or malformed evidence classifications are rejected or explicitly flagged.
- Provenance and evidence semantics are preserved through replay and normalization.

### Rollback considerations
- Rollback is feasible if evidence metadata is introduced only in a compatible, additive form.
- If evidence classification is rolled back, downstream consumers must tolerate missing or legacy metadata.

### Dependencies
- Event contract evolution
- Source and raw provenance definition
- Registry and ingestion governance requirements

### Explicit non-goals
- Not a replacement for source profile governance.
- Not a guarantee of future investigative tooling.
- Not a requirement to rework unrelated data model semantics beyond evidence classification.

---

## 2) Source profile lifecycle and activation authority

### Selected alternative
- Governed, versioned registry with explicit activation and fail-closed lookup.

### Decision summary
Source profiles are treated as authoritative, versioned metadata contracts owned by a governance authority. The system must resolve them explicitly and fail closed if they are missing, invalid, or duplicated.

### Scope boundary
- Applies to source profile registration, versioning, activation, lookup, and replay behavior.
- Includes the runtime resolution API and ownership model.

### Technical rationale
- The repository documents define source profile versioning and explicit authority requirements.
- The registry API contract already states that source profile resolution must be deterministic and fail closed.
- The architecture distinguishes parser version, source profile version, and OCSF schema version as separate identities.

### Business rationale
- Establishes a clear ownership model for source metadata and prevents drift across parser and source identity semantics.
- Supports consistent replay execution and source-aware normalization.

### Operational rationale
- Makes registry ownership explicit and formalized.
- Reduces the risk of ad hoc source metadata changes causing inconsistent processing.

### Rejected alternatives and reasons
- Ad hoc or implicit source resolution without formal lifecycle control.
  - Rejected because it undermines determinism, replay fidelity, and fail-closed behavior.

### Required contract changes
- Registry contract must specify registration, activation, version resolution, and failure semantics.
- Source profile resolution must be explicit and deterministic using the authoritative key pair.
- Replay workflows must carry the exact original profile version.

### Required implementation changes
- Formalize registry ownership and activation rules.
- Enforce versioned profile lookup and fail-closed behavior when a source or version is unknown.
- Reject duplicate or malformed profiles before activation.

### Migration implications
- Existing implicit lookup behavior must be replaced with explicit registry-driven resolution.
- Any source metadata currently embedded implicitly in runtime code or demo flows must be moved to an explicit registry flow.

### Security implications
- Reduces the chance of untrusted or silently mismatched source metadata.
- Improves integrity and predictability of normalization and replay.

### Test acceptance criteria
- Known source/profile combinations resolve deterministically.
- Unknown sources or versions fail with explicit errors.
- Duplicate registrations and malformed profiles are rejected.
- Replay uses the original profile version and resolves the same profile.

### Rollback considerations
- Rollback is practical if the registry path is introduced behind a compatibility layer.
- A rollback must preserve explicit failure semantics to avoid silent reintroduction of implicit behavior.

### Dependencies
- Source context schema
- Registry API contract
- Downstream parser and normalization execution environment

### Explicit non-goals
- Not a general-purpose metadata registry outside source profile governance.
- Not a replacement for parser lifecycle management.
- Not a requirement to change unrelated runtime configuration structures.

---

## 3) Ingestion boundary

### Selected alternative
- Formal public ingestion boundary using the raw vault and explicit raw reference handling.

### Decision summary
All raw log intake must pass through a defined public ingestion contract that stores raw payloads in the raw vault and preserves explicit references to the ingested raw content.

### Scope boundary
- Applies to raw log intake, vault storage, locator metadata, and source traceability.
- Covers both initial ingestion and any replay or investigation path that depends on raw references.

### Technical rationale
- The repository architecture explicitly describes a raw log vault and an ingestion engine.
- The system’s provenance model relies on traceable raw references rather than ad hoc direct access patterns.
- Encapsulating intake at the boundary reduces bypasses and supports consistent downstream validation.

### Business rationale
- Gives the organization a single point for source evidence preservation and auditability.
- Supports operational trust in the validity of raw inputs before parser execution.

### Operational rationale
- Standardizes how raw source data enters the pipeline.
- Improves consistency for investigation, replay, and pipeline troubleshooting.

### Rejected alternatives and reasons
- Direct service-layer or demo-path ingestion that bypasses the formal boundary.
  - Rejected because it weakens provenance and creates inconsistent raw-log handling.

### Required contract changes
- Define or formalize the public ingestion API boundary.
- Require raw-reference metadata to be preserved throughout the pipeline.
- Standardize vault linkage and raw locator semantics.

### Required implementation changes
- Ensure all raw intake uses the managed boundary rather than direct service or demo flow.
- Preserve raw references consistently for downstream parser and validation steps.
- Enforce validation of vault linkage and locator metadata.

### Migration implications
- Any demo or bypass path must be removed or isolated from the official pipeline path.
- Legacy flows that bypass vault semantics require explicit migration or compatibility handling.

### Security implications
- Improves control over raw data entry and provenance.
- Reduces the risk of untracked or unverified ingestion.

### Test acceptance criteria
- Raw intake always creates a valid vault record and raw reference.
- Direct bypass paths are rejected or excluded from the governed pipeline path.
- Stored records remain traceable to their source data.

### Rollback considerations
- Before full rollout, a fallback to previous ingest patterns requires explicit operational approval.
- Rollback steps must preserve raw record traceability and avoid orphaned data.

### Dependencies
- Raw vault storage model
- Raw reference contract
- Source provenance semantics

### Explicit non-goals
- Not a general-purpose API for arbitrary file handling.
- Not a requirement to broaden intake beyond raw log processing.
- Not a replacement for parser or normalization governance.

---

## 4) Durable raw storage and retention

### Selected alternative
- Durable raw log vault with SHA-256 digests, locator metadata, and retention policy.

### Decision summary
The project will retain raw logs in a durable vault with cryptographic digests and locator metadata, governed by a retention model that supports auditability and replay.

### Scope boundary
- Applies to raw log preservation, retention schedule, lifecycle management, and retrieval.
- Covers both the raw vault and any downstream evidence review process.

### Technical rationale
- The architecture and repository design refer to a tamper-evident raw log vault and SHA-256-digested raw content.
- Durable retention is necessary to preserve evidentiary integrity and support deterministic replay.

### Business rationale
- Enables incident response, forensic review, and compliance-oriented retention.
- Supports trust in the original raw source when downstream processing changes.

### Operational rationale
- Gives operations a clear lifecycle for raw data retention, cleanup, and retrieval.
- Reduces ambiguity around evidence preservation and archival practices.

### Rejected alternatives and reasons
- Ephemeral or in-memory storage without durable retention enforcement.
  - Rejected because it undermines auditability, replay fidelity, and evidence preservation.

### Required contract changes
- Add or formalize storage retention policy and raw-vault metadata fields.
- Document the relationship between raw digest, locator metadata, and retention rules.

### Required implementation changes
- Replace in-memory or demo-only raw handling with a durable storage model.
- Ensure stored raw payloads are digestable, retrievable, and governed by retention rules.
- Add verification and cleanup semantics consistent with retention policy.

### Migration implications
- Current in-memory storage and demo-only patterns do not satisfy the required durable model.
- Any retained raw data must be migrated or re-housed under the approved vault contract.

### Security implications
- Improves evidence preservation and tamper detection.
- Requires careful governance of retention, access, and deletion to balance audit value with data minimization.

### Test acceptance criteria
- Raw payloads stored in the vault are retrievable and match the recorded SHA-256 digest.
- Retention policy is enforced explicitly and is auditable.
- Missing or invalid locator metadata is rejected.

### Rollback considerations
- Rollback requires retaining the raw record history and any required migration metadata.
- Disposal or cleanup must not happen until rollback decisions are made and data recovery paths are checked.

### Dependencies
- Raw vault storage implementation
- Integrity model
- Retention policy and governance model

### Explicit non-goals
- Not a general-purpose long-term archival system for unrelated data.
- Not a guarantee of indefinite data retention without policy approval.
- Not a requirement to change non-raw data storage semantics.

---

## 5) Integrity and tamper-evidence

### Selected alternative
- SHA-256 payload digests with a tamper-evident chain.

### Decision summary
The project will preserve raw log integrity through SHA-256 digest checks and a tamper-evident chain so that raw payloads and derived chain state can be verified and audited.

### Scope boundary
- Applies to raw payload integrity, vault entries, and downstream assurance that no silent tampering has occurred.

### Technical rationale
- The repository’s architecture explicitly emphasizes a tamper-evident raw log vault and SHA-256 payload digests.
- Event and raw reference contracts include evidence and provenance concepts consistent with tamper-evident chain tracking.
- This model supports deterministic verification of raw content and replay fidelity.

### Business rationale
- Establishes defensible evidence handling for enterprise monitoring and incident response.
- Supports trust and auditability in downstream reporting and normalized output review.

### Operational rationale
- Provides operators with a verifiable integrity baseline for stored raw data.
- Enables detection of tampering or accidental mutation before or after processing.

### Rejected alternatives and reasons
- No explicit tamper-evident chain or integrity model beyond ad hoc validation.
  - Rejected because it leaves evidence and raw data open to undetected change and weakens trust in replay outputs.

### Required contract changes
- Add or formalize SHA-256 digest tracking and chain semantics.
- Document locator metadata and chain continuity expectations.
- Require integrity verification paths to function as fail-closed checks.

### Required implementation changes
- Ensure every raw payload is stored with a digest and locator metadata.
- Maintain a verifiable chain for raw records and derived evidence references.
- Reject or flag mismatched digest or chain state.

### Migration implications
- Existing raw data may need to be rehashed and re-linked to the chain model.
- Historical records without digest or locator metadata may need special handling or exclusion.

### Security implications
- Improves detection of unauthorized modification.
- Supports legal and operational assurance of event provenance and chain-of-custody.

### Test acceptance criteria
- Stored raw payloads match their recorded SHA-256 digest.
- Chain integrity checks fail closed on tamper or missing linkage.
- Inconsistent digest or locator metadata is visible and rejected.

### Rollback considerations
- Rollback should preserve the ability to verify earlier digest and chain state.
- Any rollback plan must not silently discard chain metadata or raw evidence.

### Dependencies
- Storage model
- Raw reference and locator metadata
- Governance and retention model

### Explicit non-goals
- Not an assurance model for unrelated system configuration files.
- Not a replacement for application-level security controls.
- Not a requirement to establish a blockchain-like ledger; the chain is a system integrity mechanism, not a distributed consensus model.

---

## 6) Governance enforcement

### Selected alternative
- Registry API enforcement, validation, and fail-closed runtime behavior.

### Decision summary
The system will enforce authoritative registry behavior through the public registry API, schema validation, and explicit fail-closed logic for unknown, malformed, or duplicate entries.

### Scope boundary
- Applies to registry resolution, source profile activation, validation, and runtime execution behavior.
- Covers policy enforcement for parser and source profile governance.

### Technical rationale
- The repository’s contract documents explicitly require deterministic resolution and fail-closed behavior.
- Registry ownership and resolution semantics are treated as a core part of the architecture, not ad hoc runtime behavior.

### Business rationale
- Gives the organization a clear ownership and change-management model for source and parser metadata.
- Reduces operational ambiguity and prevents accidental drift in runtime semantics.

### Operational rationale
- Forces explicit ownership and validation before activation.
- Creates clear failure behavior for operational incidents instead of silent fallback.

### Rejected alternatives and reasons
- Permissive runtime behavior with no formal governance enforcement.
  - Rejected because it allows undefined behavior and weakens traceability, determinism, and security posture.

### Required contract changes
- Registry API must be treated as the public, authoritative boundary.
- Validation and failure semantics must be consistent and explicit.
- Source and parser registration must be governed separately.

### Required implementation changes
- Enforce public registry access rather than private storage or unaudited direct access.
- Validate source profiles and parser definitions before activation.
- Fail closed whenever source or version data is unknown, malformed, or duplicated.

### Migration implications
- Existing ad hoc or implicit registry behavior must be replaced with formal, policy-driven access.
- Downstream runtime callers must rely on the public API rather than direct or local storage assumptions.

### Security implications
- Stronger accountability and reduced risk of unauthorized or unmanaged changes.
- Better control of what can be activated at runtime.

### Test acceptance criteria
- Only approved and valid profiles are activated.
- Unknown or invalid sources trigger explicit failure.
- Runtime behavior cannot silently fall back to unauthorized or implicit values.

### Rollback considerations
- Rollback must preserve explicit failure semantics.
- A rollback to more permissive behavior requires explicit authority and should be treated as a governance exception.

### Dependencies
- Registry API and ownership model
- Validation path for source profiles and parser definitions
- Runtime actor and operational governance

### Explicit non-goals
- Not a replacement for broader application governance.
- Not an admission of unlimited runtime bypass under emergency conditions.
- Not a requirement to broaden governance to unrelated project artifacts.

---

## Current repository comparison

### Existing repository capabilities
The current repository already contains several relevant capabilities:
- Source identity, source profile schema, and fail-closed semantics are documented in [contracts/source_context.md](../../contracts/source_context.md) and [contracts/registry_api.md](../../contracts/registry_api.md).
- The raw-vault and tamper-evident design is described in [README.md](../../README.md).
- The event contract schema includes provenance-related and integrity-related fields, indicating the intended direction for evidence and raw references.
- Registry and source-profile validation structures are present in the Python package layout under the registry and vault components.

### Contradictions or gaps relative to the approved direction
- The repository’s operational behavior still includes demo and in-memory patterns that are not equivalent to a durable raw-vault retention model.
- The public contract and architecture document describe the required governance, but the current runtime usage patterns are not yet fully aligned with those requirements.
- The current repository appears to implement portions of the intended architecture as design and demonstrator features, but not yet as a fully enforced production-grade governed system.
- Current event-model and raw-record constructs are closer to a design intent than a fully enforced production implementation.

### Required future implementation work
- Formalize the evidence classification contract and enforce it in the event model.
- Complete the governed registry lifecycle and activation path.
- Move from in-memory or demo-driven intake to a formal public ingestion boundary.
- Establish durable retention and lifecycle management for raw payload storage.
- Implement explicit SHA-256 integrity checks and chain semantics for raw records.
- Enforce fail-closed registry/API behavior across runtime execution paths.

### Open risks or unresolved questions
- Whether the team wants a single authoritative owner or a delegated governance model for registry activation.
- Whether an interim migration compatibility layer is required while legacy demo paths are phased out.
- Whether the retention policy should be fixed by policy, environment, or operational review.
- Whether any historical fixtures or sample data must be preserved as legacy compatibility artifacts until migration completion.

---

## Final status
This decision record represents the approved architectural direction for the project and is deliberately separated from the repository’s current implementation status. No code, schema, API, parser, storage, or test changes are authorized by this record.
