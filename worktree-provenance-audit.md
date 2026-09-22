# Worktree Provenance Audit

Date: 2026-09-22

## Scope and method

This is a read-only provenance assessment of the worktree items listed for review. The audit used `git status`, tracked diffs, `git log --follow`, commit history, file contents, Git path history, and filesystem metadata. No source files or existing worktree items were deleted, reverted, or modified.

The approved Phase 1 implementation files are:

- `contracts/event_contract.schema.json`
- `src/api/models.py`
- `src/api/services/event_service.py`
- `tests/integration/test_api_events.py`

The report itself is an intentional new documentation file and is not part of the Phase 1 implementation.

## Summary

| Item | Git state | Provenance conclusion | Recommended action |
|---|---|---|---|
| `src/api/main.py` | Modified, tracked | Meaningful earlier/adjacent envelope API work; beyond the narrow Phase 1 file list | Preserve and investigate separately; commit with its related envelope/API changes only after review |
| `src/normalization/mapper.py` | Modified, tracked | Meaningful source-profile and normalization-provenance work; later roadmap scope | Preserve; review as a separate later-phase change, then commit or defer intentionally |
| `src/registry/__init__.py` | Modified, tracked | Meaningful source-profile registry validation and fail-closed lookup work; Phase 2 scope | Preserve; commit as a Phase 2 change after its own review |
| `src/vault/store.py` | Modified, tracked | Small meaningful raw-vault contract compatibility addition; adjacent to later ingestion/vault work | Preserve; investigate whether it belongs with Phase 3/4 work before committing |
| `tests/integration/test_syslog_pipeline.py` | Modified, tracked | Meaningful expanded pipeline and provenance tests; later normalization/provenance scope | Preserve; separate from Phase 1 and commit with the corresponding implementation |
| `tests/normalization/test_context_injection.py` | Untracked file | Meaningful source-profile context tests; Phase 2-related | Preserve; review and commit with source-profile implementation |
| `tests/normalization/test_enrichment_provenance.py` | Untracked file | Meaningful normalization-policy provenance tests; later normalization/provenance scope | Preserve; review and commit with the corresponding implementation |
| `tests/registry/test_source_profile.py` | Untracked file | Meaningful source-profile registry tests; Phase 2-related | Preserve; review and commit with registry implementation |
| `ulpf/` | Untracked directory | Historical duplicate of the former repository root, including source, tests, fixtures, and Python caches | Do not commit as a second root; investigate before eventual removal or archival, preserving any needed history through Git |
| `t -q` | Untracked file | Accidental generated pager-help capture, not project work | Remove as an artifact after explicit cleanup approval; do not commit |

## Item findings

### `src/api/main.py`

- **Tracked status:** Tracked file with working-tree modifications.
- **Type and purpose:** Python FastAPI application entrypoint and HTTP route definitions.
- **Observed work:** The diff adds or exposes event-envelope API behavior and adapts API handling to the expanded envelope model.
- **Earlier ULPF work:** Yes, it is part of the existing ULPF API layer and is consistent with the broader event-envelope work in the worktree.
- **Roadmap relation:** Related to event-envelope/API integration, but broader than the approved Phase 1 contract-only change. It should not be treated as evidence that Phase 2 has been completed.
- **Generated or accidental:** No; the changes are structured application code.
- **Meaningful work:** Yes.
- **Recommendation:** Preserve and investigate separately. Group it with the related envelope/API changes only after confirming ownership and intended phase; do not revert automatically.

### `src/normalization/mapper.py`

- **Tracked status:** Tracked file with working-tree modifications.
- **Type and purpose:** Python normalization mapper that maps parser fields to OCSF and enriches events.
- **Observed work:** Adds source-profile lookup/context handling, timestamp and metadata injection behavior, mapping-result provenance, policy-field tracking, and related mapper parameters.
- **Earlier ULPF work:** Yes. The file has prior history in commits `7cede72`, `32a9d28`, and `2fd4dd5`.
- **Roadmap relation:** Primarily source-profile lifecycle and normalization provenance work, corresponding to the roadmap's later Phase 2 governance and adjacent normalization work. It is not required for the Phase 1 evidence enum alone.
- **Generated or accidental:** No; this is meaningful implementation code.
- **Meaningful work:** Yes.
- **Recommendation:** Preserve. Review and commit as a separate later-phase change with its tests; do not mix it into the Phase 1 approval record.

### `src/registry/__init__.py`

- **Tracked status:** Tracked file with working-tree modifications.
- **Type and purpose:** Python parser and source-profile registry implementation.
- **Observed work:** Adds source-profile registration, JSON Schema validation, duplicate detection, lookup, and `ProfileNotFoundError`/`InvalidProfileError` fail-closed behavior.
- **Earlier ULPF work:** Yes. Git history shows registry work in commits `7cede72`, `32a9d28`, `9552922`, and `2fd4dd5`.
- **Roadmap relation:** Directly related to roadmap Phase 2, “Parser registry and source-profile governance.”
- **Generated or accidental:** No; this is meaningful runtime code.
- **Meaningful work:** Yes.
- **Recommendation:** Preserve and commit separately as Phase 2 work after review and dedicated validation. Do not revert it as unrelated noise.

### `src/vault/store.py`

- **Tracked status:** Tracked file with working-tree modifications.
- **Type and purpose:** Python in-memory content-addressable raw-vault store.
- **Observed work:** Adds the canonical `STORE_TYPE = "vault"` identifier used by raw references.
- **Earlier ULPF work:** Yes. The vault implementation is part of the original ULPF repository history.
- **Roadmap relation:** Adjacent to the formal ingestion boundary and durable raw-vault work in roadmap Phases 3 and 4. The constant supports the event-envelope/raw-reference contract but does not implement durable storage or retention.
- **Generated or accidental:** No; the change is intentional and small.
- **Meaningful work:** Yes, although its phase ownership is ambiguous.
- **Recommendation:** Preserve and investigate separately. Commit with the ingestion/vault change that consumes it, or document it as a preparatory compatibility change; do not claim Phase 3 or Phase 4 completion.

### `tests/integration/test_syslog_pipeline.py`

- **Tracked status:** Tracked file with working-tree modifications.
- **Type and purpose:** Pytest integration coverage for the Syslog parser-to-normalization-to-validation pipeline.
- **Observed work:** Expands the test into mapper-golden and canonical-pipeline layers and asserts policy-field and provenance behavior.
- **Earlier ULPF work:** Yes. The file has history from the original project and was moved with the repository in commit `32a9d28`.
- **Roadmap relation:** Related to normalization, provenance, and source-profile behavior beyond the approved Phase 1 contract addition.
- **Generated or accidental:** No; it contains meaningful test coverage.
- **Meaningful work:** Yes.
- **Recommendation:** Preserve. Commit alongside the matching mapper/registry implementation after reviewing fixture compatibility and phase ownership.

### `tests/normalization/test_context_injection.py`

- **Tracked status:** Untracked file.
- **Type and purpose:** Pytest unit tests for source-profile context injection, missing-profile fail-closed behavior, incomplete context, and legacy no-context behavior.
- **Earlier ULPF work:** It is consistent with the existing ULPF source-context contracts, but this specific file has no tracked history because it is untracked.
- **Roadmap relation:** Directly related to Phase 2 source-profile governance and normalization integration.
- **Generated or accidental:** Not generated; it is authored test code. It contains one placeholder test with `pass`, which should be reviewed before commit.
- **Meaningful work:** Yes.
- **Recommendation:** Preserve and review. Commit with the source-profile implementation after replacing or explicitly documenting the placeholder test; do not include in Phase 1.

### `tests/normalization/test_enrichment_provenance.py`

- **Tracked status:** Untracked file.
- **Type and purpose:** Pytest unit tests for normalization policy fields, provenance entries, idempotence, caller precedence, and injected-field preservation.
- **Earlier ULPF work:** It aligns with the existing ULPF provenance design, but this specific file has no tracked history.
- **Roadmap relation:** Later normalization/provenance work associated with source-profile and evidence semantics, not the narrow Phase 1 contract change.
- **Generated or accidental:** Not generated; it is meaningful authored test code. The file contains a non-ASCII character in a comment, so encoding/style should be checked before commit.
- **Meaningful work:** Yes.
- **Recommendation:** Preserve and review with `src/normalization/mapper.py`; commit as a separate later-phase test change after its implementation contract is approved.

### `tests/registry/test_source_profile.py`

- **Tracked status:** Untracked file.
- **Type and purpose:** Pytest unit tests for source-profile registration, retrieval, duplicate registration, schema rejection, and registry clearing.
- **Earlier ULPF work:** It matches the existing registry and source-context contracts, but this specific file has no tracked history.
- **Roadmap relation:** Directly related to Phase 2 parser registry and source-profile governance.
- **Generated or accidental:** Not generated; it is meaningful authored test code.
- **Meaningful work:** Yes.
- **Recommendation:** Preserve and commit with `src/registry/__init__.py` after a focused Phase 2 review and validation.

### `ulpf/`

- **Tracked status:** The directory itself is untracked in the current worktree, but its contents have clear tracked history under the old path.
- **Type and purpose:** Directory containing a full duplicate ULPF repository tree, including source, tests, fixtures, contracts, documentation, and Python bytecode caches.
- **History evidence:** Commit `7cede72` created the repository under `ulpf/`. Commit `32a9d28` moved the contents from `ulpf/` to the current repository root with zero-content-change renames. Later history, including `9552922`, still references the old nested path in historical commits.
- **Earlier ULPF work:** Yes. This is historical repository structure, not newly authored current implementation.
- **Roadmap relation:** It does not represent a separate roadmap phase. It duplicates current project areas and includes old snapshots plus generated `__pycache__` files.
- **Generated or accidental:** The directory is an accidental leftover duplicate in the current worktree, although its contents are meaningful historical project material. The bytecode files inside it are generated artifacts.
- **Meaningful work:** The historical source and documentation are meaningful as provenance, but the duplicate copy should not be treated as current source of truth.
- **Recommendation:** Do not commit as a second repository root. Investigate and preserve history through Git as needed, then remove or archive the duplicate in a separately approved cleanup action. Do not modify it as part of this audit.

### `t -q`

- **Tracked status:** Untracked file.
- **Type and purpose:** Plain text file containing the help output of the `less` pager, beginning with `SUMMARY OF LESS COMMANDS`.
- **Earlier ULPF work:** No evidence of project ownership or historical ULPF purpose.
- **Roadmap relation:** None.
- **Generated or accidental:** Accidental artifact, likely created when a command intended to run pytest was interpreted as a `less` invocation or redirected its help output.
- **Meaningful work:** No. It contains no source, test, contract, or project documentation.
- **Recommendation:** Do not commit. Remove in a separately approved cleanup action; this audit does not delete it.

## Overall recommendation

The listed modified and untracked source/test items should be preserved because they contain meaningful ULPF work, but they should be separated from the approved Phase 1 change set. The registry, source-profile tests, mapper changes, and context-injection tests should be reviewed as Phase 2 work. The provenance/enrichment tests and expanded pipeline test should be grouped with the corresponding normalization work. The vault constant requires explicit phase ownership before commit.

The `ulpf/` directory and `t -q` should not be committed. `ulpf/` is a historical duplicate tree requiring a deliberate cleanup or archival decision; `t -q` is an accidental artifact suitable for eventual removal. Neither action is executed by this report.

## Audit boundary

No Phase 2 work was started by this audit. No source code, tests, contracts, or existing worktree items were changed. The only new file created is this report.