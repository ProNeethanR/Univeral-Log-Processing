# ULPF Architecture

Status: reflects the implemented, tested system as of the Corrective
Stabilization pass (2026-09-23). Supersedes the pre-implementation roadmap
language; see `docs/decisions/implementation-roadmap.md` for phase provenance.

## Pipeline overview

```
Raw log stream
   │ ingest_bytes(offset, record_index)      byte-exact capture, no decode
   ▼
Raw Log Vault (content-addressed, SHA-256, append-only chain, retention
tombstones, checkpoints)
   │
   ▼
Parser Registry ── resolves (source, version) ─▶ YAML DSL definition
   │
   ▼
DSL Interpreter (exactly 9 operations; contract-validated)
   │
   ▼
OCSF Mapper + OCSF 1.3.0 Runtime Validator (offline, frozen schema, checksummed)
   │
   ▼
ULPFEventEnvelope (contract v1.1: integrity, parser_id, parser_version,
provenance, trusted) ── quarantine failures recorded without raw content
```

## Components

- **Ingestion** (`src/ingestion/ingestor.py`): byte-level record splitting,
  exact byte-range metadata (`byte_offset_start`/`byte_offset_end`/
  `record_index`), no decode before vault capture.
- **Vault** (`src/vault/store.py`): SHA-256 content-addressed storage, exact
  byte payloads, per-record metadata (capture timestamp normalization,
  offsets, record index), append-only tamper-evident chain, retention
  tombstones (`purged_at`, chain stays valid), checkpoint-anchored
  verification reports.
- **Registry** (`src/registry/__init__.py`): versioned parser registration;
  fail-closed resolution; registration is metadata linkage only and never
  executes parser code.
- **DSL** (`src/parsers/`): `DSLValidator` enforces
  `contracts/parser_mapping.schema.json` (strict, exactly nine operations,
  no arbitrary execution). `DSLInterpreter.evaluate(field_def, state)`
  executes one operation; `ParserEngine(source, version)` resolves via the
  registry, contract-validates, then parses.
- **Normalization** (`src/normalization/`): `mapper.py` field mapping +
  provenance policy injection; `ocsf_validator.py` air-gapped validation
  against the frozen, SHA-256-pinned `schema/ocsf/ocsf_schema.json`
  (OCSF 1.3.0).
- **API** (`src/api/`): FastAPI dashboard. `main.py` mounts
  `/static` (dashboard) and exposes `/api/events`, `/api/integrity/verify`,
  `/api/integrity/checkpoint`, `/api/quarantine`, parser profile endpoints.
  Demo data initialization is explicit via framework `lifespan` when
  `ULPF_DEMO_DATA=true` (no import-time side effects).
- **Contracts** (`contracts/`): `event_contract.schema.json` (v1.1 canonical
  envelope incl. `trusted` and trust-gate semantics),
  `failure_record.schema.json` (raw-content-free quarantine records),
  `parser_mapping.schema.json` (DSL contract),
  `source_context.schema.json`.

## Trust gate

`trusted` is true only when `evidence_classification == "validated"` AND
`integrity.status == "verified"` AND `integrity.chain_verified is not False`.
An explicit `False` on the chain flag fails the gate; unknown chain state does
not.

## Determinism & reproducibility

- Demo data is not loaded at import time. Tests opt in via the `demo_data`
  fixture (`tests/conftest.py`) which isolates an ephemeral vault backend and
  snapshots/restores module state, so results are independent of import or
  collection order.
- Raw fixtures are frozen: `fixtures/SHA256SUMS`,
  `fixtures/manifest.json`, `fixtures/provenance/README.md`, and
  `fixtures/STATUS.md` were reconciled to the committed corpus and are locked
  by `tests/integration/test_fixture_integrity.py`.
- Verification commands documented in `README.md`.

## Runtime environment contracts

- `PYTHONPATH=.` — required for `python -m pytest` / `uvicorn` from the repo
  root (the code base is not installed as a package).
- `ULPF_DEMO_DATA=true` — load demo fixtures into the API at startup.
- `ULPF_VAULT_PATH` — optional override selecting the vault backend directory
  (`FileVaultBackend`). When unset, a file backend rooted at
  `%TEMP%\ulpf-vault` (i.e. `tempfile.gettempdir()/ulpf-vault`) is used; it is
  not durable across machine restarts and contents can be affected by temp
  cleanup, so production uses should set this explicitly.