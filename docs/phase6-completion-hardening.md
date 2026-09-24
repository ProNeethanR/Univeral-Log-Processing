# Phase 6 — Completion Hardening

Hardening pass addressing the seven high-risk findings from the
requirements-compliance audit. Scope was limited to integrity, retention,
contract, and failure-record correctness. No CEF/vendor workflows,
deployment, distributed storage, auth, or dashboard changes were made, and
no existing tests were weakened or removed.

## Baseline / Result

- Baseline: `PYTHONPATH=. pytest -q` → **126 passed**
- After Phase 6: `PYTHONPATH=. pytest -q` → **169 passed** (43 new tests)

> **Historical note (2026-09-23, Corrective Stabilization)**: the **169** and
> **126** figures above describe the counting at the time each write-up was
> produced and are superseded. The stabilized suite is
> **186 collected → 186 passed** with zero failures/errors/skips/warnings
> (`PYTHONPATH=. python -m pytest -q -p no:cacheprovider`), verified in the
> standard collection order and in multiple reverse/shuffled per-directory
> orders. Demo state is now deterministic and order-independent via the shared
> `demo_data` fixture (`tests/conftest.py`); `src/api/main.py` loads demo data
> through a FastAPI `lifespan` hook when `ULPF_DEMO_DATA=true`. Raw fixture
> digests were reconciled to the committed corpus (`fixtures/SHA256SUMS`,
> `fixtures/manifest.json`, `fixtures/provenance/README.md`,
> `fixtures/STATUS.md`); `tests/integration/test_fixture_integrity.py` and
> `tests/parsers/test_parser_contract.py` were added to lock those records
> in. See the stabilization report for the six-item deliverable.

## Findings Addressed

### 1. Raw-byte losslessness (demo capture path)

The demo ingestion path historically decoded, stripped, split, stripped
again, and re-encoded lines before vault capture, destroying CRLF terminators
and byte offsets.

- `split_raw_records()` / `strip_record_terminator()` in
  `src/ingestion/ingestor.py` operate on bytes only; no decode happens before
  vault capture.
- `ingest_bytes()` accepts `byte_offset_start`, `byte_offset_end`,
  `record_index` and stores them as vault metadata.
- `event_service.load_demo_data()` reads the fixture as binary and vaults
  each exact record slice; parse input is derived from the preserved bytes
  after capture.
- Tests: `tests/ingestion/test_raw_losslessness.py`,
  `tests/integration/test_demo_losslessness.py` (byte-for-byte equality,
  contiguity, offset integrity-protection, full-file reassembly).

### 2. Retention purge vs append-only integrity chain

Previously, an ordinary retention purge deleted both payload and metadata,
which broke historical chain verification.

Design: **retained integrity metadata + tombstone**.

- `purge_expired()` deletes only the `.raw` payload; the `.json` sidecar is
  retained and stamped with `purged_at` (not part of the canonical record
  hash, so existing chains stay valid — no `CHAIN_VERSION` bump).
- `verify_chain()` skips payload byte-verification only for tombstoned
  records; all linkage/hash checks still run. Deleting a raw payload
  *without* a tombstone still breaks the chain.
- Re-ingesting a purged digest restores the payload without appending a
  duplicate chain entry; original capture/retention fields (canonical hash
  inputs) stay honest, so the record can remain access-expired.
- `get()` on a purged record raises `RecordNotFoundError` (unchanged
  contract). `verify_raw_reference()` reports `missing` with an explicit
  "purged under retention policy" reason and the current chain state.
- Tests: `tests/vault/test_retention_chain.py`.

### 3. Canonical event envelope (schema 1.1)

- `ULPFEventEnvelope` now guarantees every canonical contract key:
  `provenance` is non-optional (default factory), `trusted` added,
  `integrity`/`parser_id`/`parser_version` required, `ocsf_event` may be
  null but the key is always present.
- `build_event_envelope()` is the factory that applies the trust gate;
  `is_canonical_envelope()` is a structural guard against `MappingResult` /
  mapper-dict confusion.
- Contract `schema_version` bumped **1.0 → 1.1**; required-field list updated.

### 4. Trust gate

`trusted = (evidence == validated) AND (integrity.status == verified) AND
(chain_verified is not False)`.

- Never-captured / unavailable integrity → not trusted.
- `chain_verified is None` (backend without chain support) does not fail the
  gate; only an explicit `False` does.

### 5. Checkpoint policy (verification anchors)

- `FileVaultBackend.verification_report()` now includes an explicit
  `checkpoint` block: `valid` / `missing` / `stale` / `invalid` /
  `unavailable` with sequence, head hash, and checkpoint hash.
- Overall status is `verified` **only** when the chain verifies *and* a
  checkpoint validly anchors the current chain head; anchor problems surface
  as `missing`/`stale`/`invalid` overall statuses.
- Per-record ingest verification remains chain+digest based (unchanged).
- New endpoint: `POST /api/integrity/checkpoint` (503 for unsupported
  backends, 409 when the chain cannot be checkpointed).
- Tests: `tests/vault/test_checkpoint_policy.py`; the existing
  `/api/integrity/verify` structure test was strengthened with checkpoint
  assertions.

### 6. Quarantine failure records

- `FailureRecord` (`failure_id`, `category`, `reason`, `timestamp`,
  optional `raw_ref`/`raw_hash`/`source_id`/`source_context`/`event_id`) —
  **never raw content**.
- Categories: `parse_failed`, `normalization_failed`, `validation_failed`,
  `integrity_corrupted`, `integrity_missing`, `integrity_unavailable`,
  `integrity_not_captured`.
- In-memory store: `src/api/services/quarantine_service.py`.
- Demo pipeline emits failures for parse/normalization/validation rejections
  and non-verified integrity at capture time.
- Queryable via `GET /api/quarantine` (pagination + `category`/`event_id`
  filters).
- Contract: `contracts/failure_record.schema.json`.
- Tests: `tests/integration/test_quarantine.py`.

### 7. Contract alignment

`contracts/event_contract.schema.json` (v1.1):

- `required`: now includes `integrity`, `parser_id`, `parser_version`,
  `provenance`, `trusted`.
- `raw_ref.raw_hash`: bare hex `^[0-9a-f]{64}$` (the `sha256:` prefix lives
  on `raw_ref.locator`, pattern `^sha256:[0-9a-f]{64}$`).
- `ocsf_event`: type `["object", "null"]` (key remains required).
- `trusted`: boolean trust-gate flag.

Tests: `tests/integration/test_contract_alignment.py` validates live demo
envelopes against the schema and covers the trust gate matrix.

## New / Changed Endpoints

| Endpoint | Change |
|---|---|
| `GET /api/integrity/verify` | + `checkpoint` anchor block; stricter overall status |
| `POST /api/integrity/checkpoint` | new |
| `GET /api/quarantine` | new |
| `GET /api/events/{id}/envelope` | + `trusted`; `provenance` always present |

## Explicitly Out of Scope

CEF/vendor workflows, deployment, distributed storage, auth/key management,
dashboard UI changes, weakening or removing existing tests.
