# ULPF Implementation Roadmap

## Document status
- Status: roadmap only; implementation not started
- Authority: [ulpf/docs/decisions/approved-decision-record.md](../../docs/decisions/approved-decision-record.md)
- Scope: This roadmap translates the approved architectural direction into implementation phases and work items without changing current code or configuration.

## Governing principles
- The approved decisions in [ulpf/docs/decisions/approved-decision-record.md](../../docs/decisions/approved-decision-record.md) are authoritative.
- The repository’s current implementation is treated as a reference implementation and demonstrator baseline, not as a production-grade enforcement layer.
- This roadmap separates:
  - Already implemented
  - Partially implemented
  - Missing
  - Recommended but not required
- No implementation work is authorized by this document.

---

## Phase overview

### Phase 1: Contracts and foundational types
- Establish the decision record’s contract primitives for evidence classification, raw references, and registry semantics.
- Normalize the event model and provenance contracts to the approved architectural direction.

### Phase 2: Parser registry and source-profile governance
- Formalize registry ownership, versioning, activation, and fail-closed resolution.
- Separate parser registration from source-profile registration as required by the approved decisions.

### Phase 3: Formal ingestion boundary
- Put all raw intake behind a managed public ingestion boundary.
- Standardize raw storage and raw-reference semantics.

### Phase 4: Durable raw vault and retention
- Replace in-memory or demo-only raw storage assumptions with durable raw retention semantics.
- Codify digest, retention, and locator behavior.

### Phase 5: Integrity and tamper-evidence
- Enforce SHA-256 digest verification and tamper-evident chain semantics on raw intake and stored records.

### Phase 6: Governance and fail-closed enforcement
- Enforce registry API usage, validation, and runtime failure semantics.

### Phase 7: Testing and regression hardening
- Add unit, integration, negative-path, security, and regression coverage for the approved decisions.

### Phase 8: Air-gapped deployment verification
- Verify that the project remains deterministic and offline-only, including schema validation and runtime controls.

### Phase 9: Documentation and demo completion
- Finalize project documentation, migration notes, and demo completeness so the monitored behavior is clearly separated from production requirements.

---

## Decision 1: Evidence classification

### Relevant existing repository files
- [src/api/models.py](../../src/api/models.py)
- [contracts/event_contract.schema.json](../../contracts/event_contract.schema.json)
- [src/api/services/event_service.py](../../src/api/services/event_service.py)
- [README.md](../../README.md)

### Existing capabilities that can be reused
- Already implemented:
  - Raw references and provenance metadata exist in [src/api/models.py](../../src/api/models.py).
  - Event service populates provenance data for demo output in [src/api/services/event_service.py](../../src/api/services/event_service.py).
  - Event contract schema already models raw references and provenance concepts in [contracts/event_contract.schema.json](../../contracts/event_contract.schema.json).
- Partially implemented:
  - The event envelope includes provenance-related metadata, but the “integrity” concept is intentionally omitted until chain implementation is approved in [src/api/models.py](../../src/api/models.py).
- Missing:
  - Explicit evidence classification fields and validation rules that are consistently enforced across all event records.
  - A single authoritative list of evidence states and their semantics.

### Required files to create
- New rule or contract specification for evidence classification under the existing contract area, likely adjacent to [contracts/event_contract.schema.json](../../contracts/event_contract.schema.json).
- New validation or utility module under the existing Python package structure if the project chooses to centralize evidence validation rather than keeping it in the event service.

### Required files to modify
- [src/api/models.py](../../src/api/models.py)
- [contracts/event_contract.schema.json](../../contracts/event_contract.schema.json)
- [src/api/services/event_service.py](../../src/api/services/event_service.py)
- [src/api/main.py](../../src/api/main.py) if public API response payloads must surface evidence metadata

### Required interface, API, schema, or contract changes
- Event envelope expands to include explicit evidence classification fields.
- Provenance semantics are made explicit and consistent with event contract validation.
- Raw reference and provenance semantics remain compatible with the approved architecture.

### Dependencies on other decisions
- Ingestion boundary
- Durable raw storage and retention
- Integrity and tamper-evidence
- Governance enforcement

### Implementation order
1. Define the evidence-state contract and validation rules.
2. Extend the event model and schema representation.
3. Update event creation and retrieval flows.
4. Hardening tests and negative-path validation.

### Required tests
- Unit tests for event model validation
- Integration tests for event creation and API responses
- Negative-path tests for malformed or undefined evidence classifications
- Regression tests for existing demo and fixture flows
- Security review coverage for provenance and trust assumptions

### Acceptance criteria
- Every event envelope carries an explicit evidence classification and valid provenance metadata.
- Unknown evidence states fail closed or are rejected by validation.
- API and event output remain traceable to the raw input and raw-reference metadata.

### Migration impact on existing fixtures and demo behavior
- Existing fixtures and demo data may require updates to include explicit evidence classification.
- Demo behavior may need explicit labeling to preserve traceability.
- Any legacy output without evidence metadata must be treated as non-compliant until migration is complete.

### Risks and rollback considerations
- Risk: legacy events or fixtures may not satisfy the new contract.
- Risk: incomplete provenance population may break replay semantics.
- Rollback: keep additive, backward-compatible fields where possible and clearly document any required migration before enforcement.

### Status summary
- Already implemented: partial provenance metadata in [src/api/models.py](../../src/api/models.py), [src/api/services/event_service.py](../../src/api/services/event_service.py)
- Partially implemented: event model and demo pipeline capture provenance but not full evidence classification enforcement
- Missing: explicit evidence contract, enforcement, and validation semantics
- Recommended but not required: advanced evidence status taxonomy beyond the core approved direction

---

## Decision 2: Source profile lifecycle and activation authority

### Relevant existing repository files
- [contracts/source_context.md](../../contracts/source_context.md)
- [contracts/registry_api.md](../../contracts/registry_api.md)
- [contracts/source_context.schema.json](../../contracts/source_context.schema.json)
- [src/registry/__init__.py](../../src/registry/__init__.py)
- [src/normalization/mapper.py](../../src/normalization/mapper.py)

### Existing capabilities that can be reused
- Already implemented:
  - Registry API contract and source-profile schema are present in [contracts/registry_api.md](../../contracts/registry_api.md) and [contracts/source_context.schema.json](../../contracts/source_context.schema.json).
  - Registry lookup and validation behaviors exist in [src/registry/__init__.py](../../src/registry/__init__.py).
  - The mapper attempts to resolve the source profile for runtime enrichment in [src/normalization/mapper.py](../../src/normalization/mapper.py).
- Partially implemented:
  - Registry functionality exists, but the governance model is not yet enforced as a complete lifecycle boundary.
  - Source profile resolution is present but not yet fully integrated as a controlled activation model across the entire runtime path.
- Missing:
  - Explicit owner model and regulated activation lifecycle beyond the initial registry interface.
  - Full fail-closed enforcement across all source-profile access paths.

### Required files to create
- Possible additional registry governance specification file adjacent to [contracts/registry_api.md](../../contracts/registry_api.md), if the implementation requires a separate lifecycle policy artifact.
- New enforcement or validation helper for registry activation if a dedicated module is chosen.

### Required files to modify
- [src/registry/__init__.py](../../src/registry/__init__.py)
- [contracts/registry_api.md](../../contracts/registry_api.md)
- [contracts/source_context.md](../../contracts/source_context.md)
- [src/normalization/mapper.py](../../src/normalization/mapper.py)

### Required interface, API, schema, or contract changes
- Registry must enforce explicit activation, versioned lookup, and duplicate/invalid handling.
- Runtime callers must resolve the exact original source profile version for replay.
- Source-context schema and API semantics must remain authoritative.

### Dependencies on other decisions
- Governance enforcement
- Evidence classification
- Formal ingestion boundary

### Implementation order
1. Finalize registry lifecycle and ownership semantics.
2. Add activation validation and deterministic resolution rules.
3. Connect mapper and runtime paths to explicit version-based lookup.
4. Add replay validation and fail-closed tests.

### Required tests
- Unit tests for registration, lookup, duplicate rejection, and malformed-profile rejection
- Integration tests for mapper resolution and source-context injection
- Negative-path tests for missing/unknown versions and disabled activation paths
- Regression tests for original sensor/source mappings
- Security review of source-profile trust assumptions

### Acceptance criteria
- A source profile is only active when explicitly registered and validated.
- Unknown or malformed source profiles fail closed.
- Replay resolves the original profile version deterministically.

### Migration impact on existing fixtures and demo behavior
- Current demo behavior may rely on implicit context assumptions and will need explicit source profile resolution.
- Fixtures may need source-profile metadata or explicit provenance annotations to satisfy the approved contract.

### Risks and rollback considerations
- Risk: legacy parser behavior may silently depend on implicit source metadata.
- Rollback: keep a compatibility layer only temporarily, while documenting the explicit replacement path and preserving fail-closed semantics.

### Status summary
- Already implemented: registry API contract, lookup model, and schema validation in [src/registry/__init__.py](../../src/registry/__init__.py)
- Partially implemented: resolution and validation exist, but full lifecycle enforcement and activation governance are not fully complete
- Missing: formal activation authority, replay enforcement, and end-to-end governance model
- Recommended but not required: additional registry control plane artifacts beyond the existing contract set

---

## Decision 3: Ingestion boundary

### Relevant existing repository files
- [src/ingestion/ingestor.py](../../src/ingestion/ingestor.py)
- [src/vault/store.py](../../src/vault/store.py)
- [src/api/services/event_service.py](../../src/api/services/event_service.py)
- [src/api/main.py](../../src/api/main.py)
- [contracts/event_contract.schema.json](../../contracts/event_contract.schema.json)

### Existing capabilities that can be reused
- Already implemented:
  - The ingestion module reads raw bytes and stores them in the vault in [src/ingestion/ingestor.py](../../src/ingestion/ingestor.py).
  - The raw vault stores content-addressed data and returns a locator/digest in [src/vault/store.py](../../src/vault/store.py).
  - The event service already produces raw references in demo flows in [src/api/services/event_service.py](../../src/api/services/event_service.py).
- Partially implemented:
  - There is a raw storage and retrieval mechanism, but it is not yet established as a full formal intake boundary under all runtime paths.
- Missing:
  - A public, enforced ingestion contract for all raw intake sources.
  - Guarantee that all raw data enters through the vault-backed boundary, including programmatic and demo paths.

### Required files to create
- New intake boundary contract or public API specification adjacent to existing ingestion and API packages if the implementation chooses to formalize a separate service layer.
- Additional enforcement module if the current ingestion flow is not sufficient for governance.

### Required files to modify
- [src/ingestion/ingestor.py](../../src/ingestion/ingestor.py)
- [src/vault/store.py](../../src/vault/store.py)
- [src/api/services/event_service.py](../../src/api/services/event_service.py)
- [contracts/event_contract.schema.json](../../contracts/event_contract.schema.json)

### Required interface, API, schema, or contract changes
- Public ingestion boundary must produce a raw reference and vault record before downstream processing.
- event raw_ref semantics must be enforced consistently.
- Raw reference handling must prevent direct-path bypasses.

### Dependencies on other decisions
- Durable raw storage and retention
- Integrity and tamper-evidence
- Evidence classification

### Implementation order
1. Formalize the public ingestion boundary and raw-reference contract.
2. Enforce vault insertion before parsing.
3. Update service and API paths to rely on the boundary.
4. Add negative-path tests for bypass or invalid vault references.

### Required tests
- Unit tests for ingestion file/bytes behavior
- Integration tests for raw reference creation and retrieval
- Negative-path tests for invalid files, bad bytes, or missing raw references
- Regression tests for raw provenance and demo flows

### Acceptance criteria
- All raw intake passes through the managed vault-backed boundary.
- Each raw log record carries a valid raw_ref and digest.
- Bypass paths are rejected or explicitly isolated.

### Migration impact on existing fixtures and demo behavior
- Demo behavior currently loads direct raw inputs and creates raw references in memory; a formal boundary may require explicit migration of that behavior.
- Fixtures are not a direct runtime contract, but any raw fixture ingestion must follow the same boundary semantics.

### Risks and rollback considerations
- Risk: legacy demo flows may bypass the boundary and break parity.
- Rollback: use a compatibility layer temporarily and maintain explicit traceability to the boundary because silent fallback would violate the decision.

### Status summary
- Already implemented: raw-byte storage and locator/digest generation in [src/ingestion/ingestor.py](../../src/ingestion/ingestor.py) and [src/vault/store.py](../../src/vault/store.py)
- Partially implemented: the capability exists but is not yet fully enforced as the sole public boundary
- Missing: rule enforcement, service-layer boundaries, and complete raw-reference governance
- Recommended but not required: additional ingestion telemetry and access tracking beyond the core contract

---

## Decision 4: Durable raw storage and retention

### Relevant existing repository files
- [src/vault/store.py](../../src/vault/store.py)
- [src/ingestion/ingestor.py](../../src/ingestion/ingestor.py)
- [src/api/models.py](../../src/api/models.py)
- [src/api/services/event_service.py](../../src/api/services/event_service.py)
- [fixtures/manifest.json](../../fixtures/manifest.json)

### Existing capabilities that can be reused
- Already implemented:
  - In-memory content-addressed raw storage and digesting exist in [src/vault/store.py](../../src/vault/store.py).
  - The ingestion path produces raw references and SHA-256 digests in [src/ingestion/ingestor.py](../../src/ingestion/ingestor.py).
- Partially implemented:
  - The vault model supports retrieval and verification, but it is not durable by design and is not governed by a retention policy.
- Missing:
  - Durable storage backend selection and retention lifecycle management.
  - Operational retention, archive, cleanup, and access rules.

### Required files to create
- New storage policy artifact or service layer specification, if the implementation decides to separate policy from storage logic.
- New durable backend adapter if the project moves beyond the in-memory vault model.

### Required files to modify
- [src/vault/store.py](../../src/vault/store.py)
- [src/ingestion/ingestor.py](../../src/ingestion/ingestor.py)
- [src/api/models.py](../../src/api/models.py)
- [src/api/services/event_service.py](../../src/api/services/event_service.py)

### Required interface, API, schema, or contract changes
- The raw_ref contract must be extended to specifically support durable storage and retention metadata if needed.
- Storage lifecycle and retention policy must be part of the operational contract.

### Dependencies on other decisions
- Ingestion boundary
- Integrity and tamper-evidence
- Governance enforcement

### Implementation order
1. Define durable storage backend and retention policy rules.
2. Extend the vault contract to include lifecycle semantics.
3. Enforce raw retention and retrieval behavior in the ingest path.
4. Add retention validation and cleanup tests.

### Required tests
- Unit tests for digest validity and locator generation
- Integration tests for vault retrieval, verification, and retention behavior
- Negative-path tests for invalid locator values and raw-store corruption
- Regression tests for existing raw-reference flows

### Acceptance criteria
- Raw logs are retained in a durable storage model instead of a transient in-memory-only store.
- SHA-256 digests are always produced and remain verifiable.
- Retention policy is explicit and enforceable.

### Migration impact on existing fixtures and demo behavior
- Current demo flows and in-memory stores will require migration to a durable model or an explicit compatibility layer.
- Fixtures are not storage service-critical, but any raw fixture used in demonstration or validation may need retention semantics to match the approved decision.

### Risks and rollback considerations
- Risk: storage migration may be disruptive for early demo behavior or fixture-based validation.
- Rollback: maintain a documented migration bridge and ensure raw records are not deleted until the destination storage path has been validated.

### Status summary
- Already implemented: raw-byte vault and digest generation in [src/vault/store.py](../../src/vault/store.py)
- Partially implemented: retrieval and SHA-256-based verification exist, but not durable retention enforcement
- Missing: persistent backend, retention policy, lifecycle enforcement
- Recommended but not required: archival or object-store migration strategy beyond the core approved decision

---

## Decision 5: Integrity and tamper-evidence

### Relevant existing repository files
- [src/vault/store.py](../../src/vault/store.py)
- [src/api/models.py](../../src/api/models.py)
- [src/ingestion/ingestor.py](../../src/ingestion/ingestor.py)
- [README.md](../../README.md)
- [contracts/event_contract.schema.json](../../contracts/event_contract.schema.json)

### Existing capabilities that can be reused
- Already implemented:
  - SHA-256 digest creation and verification are present in [src/vault/store.py](../../src/vault/store.py).
  - Raw reference usage is already present in [src/api/models.py](../../src/api/models.py).
- Partially implemented:
  - A raw integrity mechanism exists at the vault layer, but the full tamper-evident chain and validation enforcement are not yet implemented across the wider contract.
- Missing:
  - End-to-end tamper-evident chain semantics and enforcement on raw references and evidence records.
  - Contract-level requirement that chain continuity be verified before processing proceeds.

### Required files to create
- New chain-verification or integrity validation module, if the implementation chooses to isolate chain logic from the raw vault implementation.

### Required files to modify
- [src/vault/store.py](../../src/vault/store.py)
- [src/api/models.py](../../src/api/models.py)
- [src/ingestion/ingestor.py](../../src/ingestion/ingestor.py)
- [contracts/event_contract.schema.json](../../contracts/event_contract.schema.json)

### Required interface, API, schema, or contract changes
- Add integrity metadata and chain semantics to the event and raw-reference model.
- Require digest validation and chain verification before a record may be used as evidence or replay input.

### Dependencies on other decisions
- Durable raw storage and retention
- Evidence classification
- Governance enforcement

### Implementation order
1. Define the integrity and chain contract.
2. Enforce digest generation and verification at the raw-vault layer.
3. Add chain continuity checks and event-level integrity linkage.
4. Validate enforcement through negative-path and security tests.

### Required tests
- Unit tests for SHA-256 validation and validation mismatch behavior
- Integration tests for raw record integrity from ingestion to API exposure
- Negative-path tests for corrupted storage and invalid digest values
- Security tests for tampering and chain-breaking scenarios
- Regression tests for standard valid pipeline flows

### Acceptance criteria
- Digest mismatch or missing integrity metadata results in explicit failure.
- Stored raw records remain verifiable throughout their lifecycle.
- The chain is intact for each approved raw reference and event record.

### Migration impact on existing fixtures and demo behavior
- Fixture and demo data must be treated as legacy unless re-verified under the integrity model.
- Some current expected outputs may not satisfy chain requirements and will require explicit migration or classification.

### Risks and rollback considerations
- Risk: existing raw records without an integrity chain may be rejected by the new enforcement model.
- Rollback: keep a verification-only mode temporarily to identify non-compliant records before full enforcement.

### Status summary
- Already implemented: SHA-256 digest creation and verification in [src/vault/store.py](../../src/vault/store.py)
- Partially implemented: raw reference and integrity signals are present, but not yet a complete chain-based enforcement model
- Missing: chain continuity, full contract enforcement, and comprehensive tamper detection flow
- Recommended but not required: additional integrity evidence or ledger-style audit model beyond the approved chain-based approach

---

## Decision 6: Governance enforcement

### Relevant existing repository files
- [contracts/registry_api.md](../../contracts/registry_api.md)
- [contracts/source_context.md](../../contracts/source_context.md)
- [src/registry/__init__.py](../../src/registry/__init__.py)
- [src/normalization/mapper.py](../../src/normalization/mapper.py)
- [src/api/main.py](../../src/api/main.py)

### Existing capabilities that can be reused
- Already implemented:
  - Registry API contract and fail-closed semantics are described in [contracts/registry_api.md](../../contracts/registry_api.md).
  - Registry lookup and validation are implemented in [src/registry/__init__.py](../../src/registry/__init__.py).
  - The mapper already consults the source profile at runtime in [src/normalization/mapper.py](../../src/normalization/mapper.py).
- Partially implemented:
  - The governance model exists in design and partial runtime behavior, but not yet as a uniformly enforced project-wide runtime control.
- Missing:
  - A unified fail-closed enforcement path across registry resolution, parsing, ingestion, and replay control.
  - Clear runtime policy enforcement for unknown or invalid sources.

### Required files to create
- New governance enforcement layer or validation helper adjacent to the service and registry packages if implementation chooses to centralize guardrails outside the registry module.

### Required files to modify
- [src/registry/__init__.py](../../src/registry/__init__.py)
- [src/normalization/mapper.py](../../src/normalization/mapper.py)
- [src/api/main.py](../../src/api/main.py)
- [contracts/registry_api.md](../../contracts/registry_api.md)
- [contracts/source_context.md](../../contracts/source_context.md)

### Required interface, API, schema, or contract changes
- Public registry API becomes the single authoritative access path.
- Runtime failures for invalid or missing source profiles must be explicit and fail closed.
- Validation and enforcement logic must be consistently applied before activation or processing.

### Dependencies on other decisions
- Source profile lifecycle and activation authority
- Ingestion boundary
- Evidence classification
- Integrity and tamper-evidence

### Implementation order
1. Finalize the governance policy and enforcement boundary.
2. Add fail-closed checks to registry resolution and runtime activation.
3. Validate the ingestion and mapping paths against those checks.
4. Add governance, security, and negative-path coverage.

### Required tests
- Unit tests for registry validation and fail-closed error paths
- Integration tests across mapping, registry, and ingestion flows
- Negative-path tests for malformed, missing, and duplicate registrations
- Security tests to ensure runtime cannot silently fall back to implicit state
- Regression tests for known valid events and fixtures

### Acceptance criteria
- Unknown or invalid registry entries do not activate.
- Source/profile access is consistent and deterministic.
- Runtime behavior fails explicitly rather than silently falling back.

### Migration impact on existing fixtures and demo behavior
- Demo and fixture-driven flows may depend on implicit assumptions; those assumptions must be made explicit or replaced.
- Replay must resolve the original source profile version and cannot rely on implicit runtime defaults.

### Risks and rollback considerations
- Risk: legacy runtime behavior may appear to work while violating the governance model.
- Rollback: governance enforcement should be introduced behind a documented compatibility window, but only if the public API boundary remains explicit and fail closed.

### Status summary
- Already implemented: registry validation and lookup interfaces in [src/registry/__init__.py](../../src/registry/__init__.py)
- Partially implemented: some runtime access paths are aware of source profile and validation semantics
- Missing: full interlocked governance enforcement across all runtime and replay paths
- Recommended but not required: dedicated operational policy tooling beyond the approved decision scope

---

## Cross-cutting testing plan

### Unit tests
- Event model validation and contract compliance
- Source profile registration, retrieval, invalid profile rejection, and duplicate detection
- Vault digest generation, retrieval, and verification
- Ingestion boundary behavior for valid and invalid input
- Governance enforcement failure cases

### Integration tests
- End-to-end pipeline from ingestion through parsing, normalization, validation, and API response
- Source-profile resolution during mapping and replay
- Raw reference continuity from vault to event envelope

### Negative-path tests
- Missing or malformed source profiles
- Corrupted vault entries
- Unknown versions and invalid parser metadata
- Invalid event evidence classification
- Duplicate registrations and registry bypass attempts

### Security tests
- Tampering detection against stored raw bytes and digests
- Validation of fail-closed behavior for registry and source-profile resolves
- Check that bypass paths do not silently bypass the ingestion boundary
- Review of trust assumptions around source metadata and runtime defaults

### Regression tests
- Existing fixtures in [fixtures/ground_truth](../../fixtures/ground_truth) and expected output flow
- Runtime smoke tests for API behavior in [src/api/main.py](../../src/api/main.py)
- Existing parser validation path in [src/parsers/engine.py](../../src/parsers/engine.py) and [src/parsers/interpreter.py](../../src/parsers/interpreter.py)

---

## Phase-by-phase execution summary

### Phase 1: Contracts and foundational types
- Modify/extend the event model and contract definitions.
- Align raw reference and provenance semantics with the approved evidence direction.
- Existing files: [src/api/models.py](../../src/api/models.py), [contracts/event_contract.schema.json](../../contracts/event_contract.schema.json)

### Phase 2: Parser registry and source-profile governance
- Harden registry lifecycle and source profile activation.
- Existing files: [src/registry/__init__.py](../../src/registry/__init__.py), [contracts/registry_api.md](../../contracts/registry_api.md), [contracts/source_context.md](../../contracts/source_context.md)

### Phase 3: Formal ingestion boundary
- Formalize raw intake and raw reference handling.
- Existing files: [src/ingestion/ingestor.py](../../src/ingestion/ingestor.py), [src/api/services/event_service.py](../../src/api/services/event_service.py)

### Phase 4: Durable raw vault and retention
- Move the project to a durable raw storage model with explicit retention semantics.
- Existing files: [src/vault/store.py](../../src/vault/store.py)

### Phase 5: Integrity and tamper-evidence
- Enforce digest and chain verification across raw records and event references.
- Existing files: [src/vault/store.py](../../src/vault/store.py), [src/api/models.py](../../src/api/models.py)

### Phase 6: Governance and fail-closed enforcement
- Enforce API, source-profile, and runtime guardrails.
- Existing files: [src/registry/__init__.py](../../src/registry/__init__.py), [src/normalization/mapper.py](../../src/normalization/mapper.py), [src/api/main.py](../../src/api/main.py)

### Phase 7: Testing and regression hardening
- Add test coverage across the six decisions.
- Relevant files: existing test directories under [tests](../../tests)

### Phase 8: Air-gapped deployment verification
- Verify deterministic runtime without external dependency or schema drift.
- Relevant files: [README.md](../../README.md), [schema/OCSF_VERSION.md](../../schema/OCSF_VERSION.md), [schema/ocsf/ocsf_schema.json](../../schema/ocsf/ocsf_schema.json)

### Phase 9: Documentation and demo completion
- Update demo and documentation artifacts so the approved production direction is clearly separated from current demo behavior.
- Relevant files: [README.md](../../README.md), [docs/architecture.md](../../docs/architecture.md)

---

## Current status by implementation class

### Already implemented
- Source profile schema and registry lookup basics: [contracts/source_context.schema.json](../../contracts/source_context.schema.json), [src/registry/__init__.py](../../src/registry/__init__.py)
- Raw vault storage and SHA-256 digests: [src/vault/store.py](../../src/vault/store.py)
- Ingestion bytes/file intake and raw reference creation: [src/ingestion/ingestor.py](../../src/ingestion/ingestor.py)
- Event provenance and raw-ref model: [src/api/models.py](../../src/api/models.py)
- Parser and OCSF validation mechanics: [src/parsers/engine.py](../../src/parsers/engine.py), [src/normalization/mapper.py](../../src/normalization/mapper.py), [src/normalization/ocsf_validator.py](../../src/normalization/ocsf_validator.py)

### Partially implemented
- Governance policy expressed in contracts but not uniformly enforced in runtime usage
- Evidence classification and integrity chain semantics are conceptually present but not fully enforced across all event flow paths
- Demo pipeline behavior has operational and provenance design intent but is not equivalent to a production-governed boundary

### Missing
- Durable retention policy for stored raw logs
- Formal public ingestion boundary enforcement for all inputs
- End-to-end tamper-evident chain semantics
- Full source-profile lifecycle enforcement and fail-closed runtime activation
- Complete evidence classification contract and validation enforcement

### Recommended but not required
- Additional internal policy docs beyond the current contract set
- Extra operational telemetry or retention dashboards
- Long-term archival and compliance tooling beyond the immediate approved architectural direction

---

## Risk log
- Legacy demo flows may mask the need for formal lifecycle controls.
- The repository appears to contain a reference implementation and demonstrator behavior that partially overlaps with the approved production direction but does not yet enforce it.
- The raw-vault capability exists, but durable retention and lifecycle enforcement are not complete.
- Source profile and registry semantics are documented and partially implemented, but not yet fully enforced across all runtime paths.
- Evidence classification and integrity chain semantics may require careful migration handling for historical fixtures and demo content.

## Rollback considerations
- Preserve a staged migration path with clear compatibility boundaries.
- Keep the approved decision record authoritative and separate from current runtime behavior.
- Do not use late-stage rollback to replace a decision with an unapproved alternative.
- Document any temporary compatibility layer explicitly as transitional and reversible.

## Final status
This document is a roadmap only. It does not authorize implementation or modify repository behavior.
