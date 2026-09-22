# Repository Baseline Reconciliation Plan

Date: 2026-09-22

## Authority and scope

This documentation-only plan reconciles the worktree items listed in [worktree-provenance-audit.md](worktree-provenance-audit.md) against the approved architectural direction in `ulpf/docs/decisions/approved-decision-record.md` and the phase boundaries in `ulpf/docs/decisions/implementation-roadmap.md`.

No source code, tests, contracts, existing artifacts, or Git history are changed by this plan. No cleanup, move, revert, or commit is authorized or executed here.

The approved Phase 1 implementation set is:

- `contracts/event_contract.schema.json`
- `src/api/models.py`
- `src/api/services/event_service.py`
- `tests/integration/test_api_events.py`

The baseline reconciliation must keep that Phase 1 set distinguishable from work that is earlier, later, historical, or accidental.

## Classification and disposition matrix

| Item | Classification | Recommended action | Next-phase inclusion |
|---|---|---|---|
| `src/api/main.py` | Earlier legitimate work | Investigate further | No, unless a Phase 1 compatibility review proves it is required |
| `src/normalization/mapper.py` | Later-phase work already present | Commit separately | Yes, as Phase 2 implementation input after review |
| `src/registry/__init__.py` | Later-phase work already present | Commit separately | Yes, as Phase 2 implementation input after review |
| `src/vault/store.py` | Later-phase work already present | Investigate further | No; defer to Phase 3/4 ownership unless a narrow contract dependency is documented |
| `tests/integration/test_syslog_pipeline.py` | Later-phase work already present | Commit separately | Yes, with the matching normalization/registry work, not as unowned Phase 1 scope |
| `tests/normalization/test_context_injection.py` | Later-phase work already present | Commit separately | Yes, for Phase 2 source-profile governance validation |
| `tests/normalization/test_enrichment_provenance.py` | Later-phase work already present | Commit separately | No initial Phase 2 dependency unless its mapper provenance contract is explicitly included |
| `tests/registry/test_source_profile.py` | Later-phase work already present | Commit separately | Yes, for Phase 2 registry validation |
| `ulpf/` | Historical duplicate | Remove after explicit confirmation | No |
| `t -q` | Accidental artifact | Remove after explicit confirmation | No |

## Item reconciliation details

### `src/api/main.py`

- **Git state:** Modified tracked file.
- **Classification:** Earlier legitimate work, with adjacent event-envelope API changes.
- **Recommended action:** Investigate further, then preserve in its current location unless a separate reviewed commit is warranted.
- **Why:** The file is a real FastAPI entrypoint and its changes expose or adapt envelope behavior. The audit does not establish that all of its changes belong to the approved Phase 1 contract-only set, but it also provides no basis for treating them as accidental.
- **Functionality loss risk:** Reverting or dropping the changes could remove event-envelope API compatibility or route behavior. No rollback should be attempted until route consumers and the Phase 1 API tests are compared.
- **Test dependency:** `tests/integration/test_api_events.py` and API startup behavior may depend on it. Confirm with the focused API test before any disposition.
- **Phase 2 inclusion:** No. It should be resolved as baseline/API compatibility work before Phase 2, or explicitly carried as a separate earlier-work commit.

### `src/normalization/mapper.py`

- **Git state:** Modified tracked file.
- **Classification:** Later-phase work already present.
- **Recommended action:** Commit separately after review; preserve in the current location until that reviewed commit is made.
- **Why:** The changes implement source-profile resolution, context injection, mapping provenance, and policy-field tracking. These align directly with the approved governed, versioned registry and fail-closed source-profile direction and the roadmap's Phase 2 work.
- **Functionality loss risk:** Reverting it could remove source-profile timestamp/metadata enrichment and provenance behavior. Existing normalization and source-context tests would lose their implementation target.
- **Test dependency:** `tests/integration/test_syslog_pipeline.py`, `tests/normalization/test_context_injection.py`, and `tests/normalization/test_enrichment_provenance.py` exercise this behavior.
- **Phase 2 inclusion:** Yes, as existing candidate implementation to review, not as assumed-complete Phase 2 work. Activation authority, replay semantics, and all-path fail-closed enforcement remain to be verified.

### `src/registry/__init__.py`

- **Git state:** Modified tracked file.
- **Classification:** Later-phase work already present.
- **Recommended action:** Commit separately after review; preserve in the current location until its focused validation and ownership are settled.
- **Why:** It adds source-profile registration, schema validation, duplicate rejection, lookup, and explicit missing/invalid errors. These are direct Phase 2 registry capabilities under the approved decision record.
- **Functionality loss risk:** Dropping the changes could remove source-profile registration and fail-closed lookup behavior, causing mapper tests and source-aware normalization to fail or silently regress.
- **Test dependency:** `tests/registry/test_source_profile.py` and source-profile paths in `tests/normalization/test_context_injection.py` depend on it.
- **Phase 2 inclusion:** Yes. It is a primary Phase 2 implementation candidate, but it must not be declared complete until activation governance, deterministic version resolution, and runtime-path coverage are verified.

### `src/vault/store.py`

- **Git state:** Modified tracked file.
- **Classification:** Later-phase work already present.
- **Recommended action:** Investigate further; then preserve or commit separately with explicit Phase 3/4 ownership.
- **Why:** The `STORE_TYPE` addition supports the raw-reference contract, but the underlying store remains in-memory. The roadmap assigns formal ingestion to Phase 3 and durable retention to Phase 4, so this small compatibility change should not be folded into Phase 2 by implication.
- **Functionality loss risk:** Removing it could break raw-reference serialization or event-envelope construction that expects the canonical store identifier.
- **Test dependency:** API/event-envelope integration behavior and any raw-reference assertions may depend on the constant, including `tests/integration/test_api_events.py`.
- **Phase 2 inclusion:** No, unless a reviewed Phase 2 contract test demonstrates a direct dependency. Otherwise defer it to the ingestion/vault workstream.

### `tests/integration/test_syslog_pipeline.py`

- **Git state:** Modified tracked file.
- **Classification:** Later-phase work already present.
- **Recommended action:** Commit separately with the matching mapper/registry changes after test review.
- **Why:** It adds layered mapper and canonical-pipeline coverage plus policy/provenance assertions. Those tests describe later normalization behavior rather than the narrow Phase 1 evidence-classification addition.
- **Functionality loss risk:** Reverting the changes would reduce coverage of normalization and provenance behavior, but should not remove production functionality by itself.
- **Test dependency:** It is itself a test dependency for the modified mapper and enrichment behavior; its assumptions must be reconciled with the approved source-profile and provenance contracts.
- **Phase 2 inclusion:** Yes for the source-profile and normalization integration subset. Keep broader enrichment assertions separate if they are not required by the Phase 2 acceptance criteria.

### `tests/normalization/test_context_injection.py`

- **Git state:** Untracked file.
- **Classification:** Later-phase work already present.
- **Recommended action:** Commit separately with the registry/mapper implementation after review.
- **Why:** It tests explicit source-profile resolution, missing-profile failure, incomplete context, and no-context compatibility. Those are direct Phase 2 concerns.
- **Functionality loss risk:** The file is test-only, so removing it would not directly remove runtime functionality, but it would remove regression protection for source-profile governance and legacy behavior.
- **Test dependency:** It depends on `src/registry/__init__.py` and `src/normalization/mapper.py`.
- **Phase 2 inclusion:** Yes. Before commit, resolve the placeholder `pass` test so the acceptance claim is meaningful.

### `tests/normalization/test_enrichment_provenance.py`

- **Git state:** Untracked file.
- **Classification:** Later-phase work already present.
- **Recommended action:** Commit separately after the mapper provenance contract is explicitly scoped and reviewed.
- **Why:** It tests policy-field provenance, idempotence, caller precedence, and injected-field preservation. This is meaningful normalization work, but the roadmap does not make every advanced provenance assertion a Phase 2 entry dependency.
- **Functionality loss risk:** No direct runtime loss because it is test-only; deleting or omitting it would lose important regression coverage for provenance semantics.
- **Test dependency:** It depends on the modified mapper's `MappingResult` and enrichment behavior.
- **Phase 2 inclusion:** Not required for Phase 2 entry. Include only if the Phase 2 implementation contract explicitly adopts these provenance guarantees; otherwise preserve for the later normalization/provenance validation set.

### `tests/registry/test_source_profile.py`

- **Git state:** Untracked file.
- **Classification:** Later-phase work already present.
- **Recommended action:** Commit separately with the registry implementation after focused review.
- **Why:** It covers registration, retrieval, duplicate rejection, malformed-profile rejection, and registry clearing. These map directly to the approved Phase 2 test acceptance criteria.
- **Functionality loss risk:** No direct runtime loss because it is test-only, but omitting it would remove the clearest regression coverage for fail-closed registry behavior.
- **Test dependency:** It depends on `src/registry/__init__.py` and `contracts/source_context.schema.json`.
- **Phase 2 inclusion:** Yes, after confirming the tests cover the final activation and version-resolution contract rather than only the current preliminary API.

### `ulpf/`

- **Git state:** Untracked directory in the current worktree; its content has historical tracked provenance under the former repository root.
- **Classification:** Historical duplicate.
- **Recommended action:** Remove after explicit confirmation. Do not commit or move it as part of baseline reconciliation.
- **Why:** Git history shows the original nested `ulpf/` tree was moved to the repository root in commit `32a9d28`; the current directory duplicates the former root and includes stale Python caches. It is not the current source of truth.
- **Functionality loss risk:** Removing the duplicate should not lose current functionality because the current root contains the project. Historical content and provenance remain recoverable through Git history. Before removal, verify that it contains no untracked-only work absent from the root.
- **Test dependency:** The current test suite should not depend on the nested duplicate when run from the repository root. Verify import paths and test discovery before cleanup.
- **Phase 2 inclusion:** No. It must be excluded from Phase 2 scope and from any commit intended to advance the implementation.

### `t -q`

- **Git state:** Untracked file.
- **Classification:** Accidental artifact.
- **Recommended action:** Remove after explicit confirmation.
- **Why:** Its contents are `less` pager help, not ULPF source, documentation, fixtures, or tests. It has no project history or roadmap relationship.
- **Functionality loss risk:** None identified.
- **Test dependency:** None identified; confirm with a repository-wide text/path search before removal if operational caution is required.
- **Phase 2 inclusion:** No.

## Safe Git checkpoint strategy

The following is the recommended rollback strategy. It is a plan only; no Git commands are executed by this document.

1. Capture the current baseline with `git status --short --branch`, `git diff --binary`, and an inventory of untracked paths. Store the outputs outside the worktree or in an approved audit location.
2. Create a temporary safety reference at the current `HEAD`, such as an annotated tag or branch created with explicit approval. Do not commit the worktree changes as part of this checkpoint.
3. Preserve the complete worktree patch, including untracked files, with a reviewed patch/archive procedure before any cleanup. The archive must include file paths, binary contents where applicable, and a manifest of hashes.
4. Run the full regression suite from the checkpoint with the established environment configuration: `PYTHONPATH=.` and the repository's supported Python environment. Record the result.
5. Reconcile only one disposition group at a time: Phase 1 baseline, earlier legitimate work, Phase 2 candidate work, later deferred work, historical duplicate, and accidental artifact.
6. After each group, record `git status`, the relevant diff, test results, and a rollback reference. If behavior or provenance becomes uncertain, restore the group from the patch/archive and stop that group.
7. Do not delete the safety reference or patch/archive until the reconciled baseline has passed the full regression suite and the user has approved the resulting checkpoint.

The important rollback invariant is that no cleanup action should rely on an irreversible working-tree operation. A clean checkpoint must be recoverable both to the pre-reconciliation worktree and to the approved Phase 1-only baseline.

## Conditions before Phase 2 begins

Phase 2 must not begin until every condition below is satisfied:

1. The approved Phase 1 files are identified and separated from all other worktree changes.
2. The full repository regression suite passes from the chosen clean baseline, with total, passed, failed, error, skipped, and warning counts recorded.
3. `src/api/main.py` has been resolved as earlier legitimate work or explicitly included in a reviewed compatibility commit; it is not left ambiguously mixed into the Phase 1 baseline.
4. The source-profile candidate set is explicit: `src/registry/__init__.py`, `src/normalization/mapper.py`, `tests/registry/test_source_profile.py`, and `tests/normalization/test_context_injection.py` are either preserved as the Phase 2 starting set or deliberately deferred with documented reasons.
5. The Phase 2 contract boundary is documented: registry ownership, profile versioning, explicit activation, deterministic lookup, duplicate rejection, malformed-profile rejection, and fail-closed behavior are testable requirements.
6. Any source-profile implementation already present is treated as partial candidate work, not as completed Phase 2, until activation authority, replay/version resolution, and all relevant runtime paths are validated.
7. The vault change in `src/vault/store.py` has an explicit owner and is either documented as a dependency or deferred to Phase 3/4. Phase 2 must not silently expand into formal ingestion, durable retention, or tamper-evidence.
8. `ulpf/` is excluded from the active source tree and no current-only work exists solely inside it; its eventual cleanup or archival disposition is approved separately.
9. `t -q` is identified as non-project output and excluded from all implementation commits; its removal is separately approved.
10. The Phase 2 test set is agreed before implementation begins, including registry unit tests, source-profile integration tests, missing/unknown version negative paths, duplicate/malformed profile paths, and compatibility behavior for existing parser flows.
11. A Git checkpoint and recoverable worktree patch/archive exist, and the rollback procedure has been reviewed.
12. The user explicitly authorizes Phase 2 implementation after reviewing the reconciled baseline and these entry conditions.

## Final boundary

This document creates a reconciliation plan only. It does not delete, revert, move, commit, or modify any audited item, and it does not start Phase 2.