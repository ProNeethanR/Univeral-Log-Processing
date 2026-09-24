# ULPF Corrective Stabilization — Final Report

Date: 2026-09-23
Repository: `P:\Univeral Log Processing`
Mode: Corrective Stabilization (no product features added; no Phase 7
expansion; read-only audit previously accepted, files modified here).

All changes remain **uncommitted**. No commit was made or authorized.

---

## 1. Files changed

### Source (defect fixes)
- `src/vault/store.py` — `_normalize_capture_timestamp()` added; `_metadata_for()`
  now honors caller-supplied ISO-8601 capture timestamps (strings, including
  `Z`), raising `ValueError` on bad input instead of silently falling back to
  "now" (CD-1).
- `src/ingestion/ingestor.py` — `ingest_file` now emits
  `byte_offset_start=0, byte_offset_end=len(raw_bytes), record_index=1`;
  `ingest_batch` emits `record_index=index+1` (CD-2/CD-3).
- `src/api/services/event_service.py` — `load_demo_data()` is now
  deterministic: clears `_events`, `_summaries`, `quarantine_service._failures`,
  resets `_active_parsers=0` before reloading. Import-time demo load removed
  (CD-4).
- `src/api/services/run_service.py` — import-time `_init()` replaced by
  `ensure_demo_run()` (deterministic run/run-event rebuild, CD-4).
- `src/api/main.py` — `bootstrap_demo()` + FastAPI `lifespan` (replaces
  deprecated `@app.on_event("startup")`); `/static` mount preserved.

### Tests
- `tests/conftest.py` (new) — shared `isolated_vault` + `demo_data` fixtures
  (snapshot/restore of env, events, summaries, failures, runs, active parsers).
- `tests/ingestion/test_end_to_end_preservation.py` — rewritten (TD-1/TD-2):
  per-record byte-slice comparison; multiline + batch exactness; metadata test
  uses a near-future capture timestamp (avoids expiry-dedup with the now-fixed
  timestamp handling); autouse isolated vault.
- `tests/integration/test_api_events.py` — uses `demo_data` (TD-3/TD-4), no
  vacuous-empty skips; asserts real counts.
- `tests/integration/test_quarantine.py` — `demo_data`; asserts non-empty demo
  failures and `failed⊆quarantined`.
- `tests/integration/test_contract_alignment.py` — `demo_data`; live demo
  envelopes validated against the contract.
- `tests/integration/test_demo_losslessness.py` — shared `demo_data`; removed
  redundant local fixture and module-level env set.
- `tests/integration/test_fixture_integrity.py` (new) — locks `SHA256SUMS` and
  `manifest.json` to the on-disk corpus (FI-1).
- `tests/parsers/test_parser_contract.py` (new) — ships `parsers/syslog.yaml`
  against `contracts/parser_mapping.schema.json`; nine-op enum check.

### Fixture records (reconciliation)
- `fixtures/SHA256SUMS`, `fixtures/manifest.json`,
  `fixtures/provenance/README.md`, `fixtures/STATUS.md` — regenerated to the
  committed corpus (see §3).

### Docs
- `README.md` — corrected test count (186), replaced fabricated DSL/grok
  example with the real `ParserEngine(parser_id, version)` + `DSLInterpreter`
  API, added runtime env contracts, listed `docs/architecture.md`.
- `docs/architecture.md` — filled (was 0 bytes) with the implemented-system
  architecture and runtime contracts.
- `docs/decisions/implementation-roadmap.md` — reconciliation header marking
  the pre-implementation plan historical.
- `docs/phase6-completion-hardening.md` — addendum recording the stabilized
  186-pass result and superseding the 126/169 counts.

---

## 2. Defects fixed (with evidence)

| ID | Defect | Fix |
|----|--------|-----|
| CD-1 | ISO capture timestamps ignored (fallback "now") | `_normalize_capture_timestamp` |
| CD-2/CD-3 | `ingest_file`/`ingest_batch` recorded no offset/record_index metadata | offsets + record indices stored |
| CD-4 | Demo state loaded at import time → order-dependent tests | explicit `lifespan` bootstrap + `demo_data` fixture |
| TD-1 | Whole-file-per-record comparison masked slicing bugs | per-record byte-slice assertions |
| TD-2 | Test reached into `event_service._events` via StopIteration | isolated vault + slice re-capture |
| TD-3/TD-4 | Filter/endpoint tests skipped on empty data | real positive assertions via `demo_data` |
| TD-5 | Quarantine/run assertions vacuous on empty state | non-empty guards + subset checks |
| FI-1 | SHA256SUMS/manifest described non-existent content | regenerated to committed corpus + integrity test |
| DOC | README DSL example described a nonexistent API; count wrong | real API example; corrected count |
| API | deprecation warning from `@app.on_event` | migrated to `lifespan` |

No existing assertion was weakened to make the suite pass; vacuous guards were
replaced with positive assertions backed by deterministic demo data.

---

## 3. Fixture reconciliation (FI-1)

- Authoritative corpus = committed on-disk files (`git status` clean for
  `fixtures/`; matches `recovery-manifest.md` of 2026-09-22).
- Corrected 3 records (oct 2026-09-18 values described pre-edit content):
  - `cef-real-001.log` `755326d1…/1628` → `ca37d406…/1629`
  - `cef-doc-examples.log` `b80b3a48…/1095` → `bf84db1e…/1105`
  - `fortigate-001.log` `162edcbc…/8905` → `21a07d34…/8926`
- `syslog-001.log` unchanged `a3783b7c…/5330` (matched disk).
- Freeze decision recorded in `fixtures/STATUS.md`. Locked by
  `tests/integration/test_fixture_integrity.py`.

---

## 4. Tests executed — exact results

Command: `PYTHONPATH=. python -m pytest -q -p no:cacheprovider`

| Run | Result |
|-----|--------|
| Full suite (standard order) x4 during work | **186 passed** each, 0 failures/errors/skips/warnings |
| Per-directory: registry | 17 passed |
| Per-directory: normalization | 40 passed |
| Per-directory: parsers | 31 passed (pre-parser-contract; +3 later = 34) |
| Per-directory: vault | 33 passed |
| Per-directory: ingestion | 33 passed |
| Per-directory: integration | 29 passed |
| Reverse collection order | 186 passed |
| Alternating per-directory collection order | 186 passed |
| Contract (jsonschema) | demo envelopes vs `event_contract.schema.json` (in-suite); `parsers/syslog.yaml` vs `parser_mapping.schema.json` (in-suite) |

Sum of per-directory runs = 17+40+31+33+33+29 = **183** (ran while only
`test_fixture_integrity.py` had been added: 181 baseline + 2). Both reverse
(`integration ingestion vault parsers normalization registry`) and alternating
(`parsers ingestion normalization registry vault integration`) collection
orders were rerun after `tests/parsers/test_parser_contract.py` (3 tests) was
added and each reported **186 passed**. All orders agree →
import/collection-order independence is proven.

---

## 5. Remaining risks (out of scope this phase)

- `requirements.txt:9` lists non-existent `httpx2>=0.1.0` (ENV-4).
- `src/ingestion/ingestor.py:20` `sys.path.insert` import hack (ENV-1).
- Default vault backend is a file volume under `%TEMP%` (ENV-3) unless
  `ULPF_VAULT_PATH` is set — not durable/production-grade.
- Tracked junk artifacts: `honeynet.log`, `honeynet.log.gz`, `t -q`,
  0-byte `docker-compose.yml`.
- Registry state is in-memory; no persistence (MI scope).
- CEF real-world coverage is a single sample (documented smoke-test
  limitation); FortiGate fixture is real but sourced without explicit license.

---

## 6. Phase verdicts

### Phase 6 acceptance — **PASS** (deterministic)
- Suite green and order-independent across multiple collection orders.
- Contract alignment (envelope v1.1, parser DSL, failure records) enforced by
  tests. Fixture corpus frozen and integrity-checked. Corrective Stabilization
  objectives complete.

### Phase 7 go/no-go — **NO-GO** (as defined in-scope) / recommended **GO** for
the enumerated remediation of remaining risks
- The out-of-scope Phase 7 candidates above (CEF/FortiGate parser depth,
  registry persistence, deployment, docker infra) are not started. If Phase 7
  is defined as *resolving those remaining risks*, proceed; if it is defined
  as *further product features*, it conflicts with the stabilization mandate
  and is not authorized.

---

## File inventory changed (git status at handoff)

Modified: `README.md`, `contracts/event_contract.schema.json`,
`docs/architecture.md`, `docs/decisions/implementation-roadmap.md`,
`fixtures/SHA256SUMS`, `fixtures/STATUS.md`, `fixtures/manifest.json`,
`fixtures/provenance/README.md`, `src/api/main.py`, `src/api/models.py`,
`src/api/services/event_service.py`, `src/api/services/run_service.py`,
`src/ingestion/ingestor.py`, `src/vault/store.py`,
`tests/integration/test_api_events.py`

Untracked (pre-existing or new): `contracts/failure_record.schema.json`,
`docs/phase6-completion-hardening.md`,
`src/api/services/quarantine_service.py`, `tests/conftest.py`,
`tests/ingestion/test_end_to_end_preservation.py`,
`tests/ingestion/test_raw_losslessness.py`,
`tests/integration/test_contract_alignment.py`,
`tests/integration/test_demo_losslessness.py`,
`tests/integration/test_fixture_integrity.py`,
`tests/integration/test_quarantine.py`,
`tests/parsers/test_parser_contract.py`,
`tests/vault/test_checkpoint_policy.py`, `tests/vault/test_retention_chain.py`

Nothing committed.