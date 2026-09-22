# Recovery Archive Verification

Generated: 2026-09-22

## Snapshot

- Archive: `P:\ULPF-recovery-20260922.zip`
- Manifest: `recovery-manifest.md`
- Current HEAD captured: `95ba189`
- Archive scope: all files under the repository except `.git`, including tracked, untracked, ignored recovery files, `ulpf`, `t -q`, and `recovery-manifest.md`.

## Hashes

- Archive SHA-256: `D41CECC93FBCAD374BA29169A9AA154DC74C03F70A27C21650522D74C48E81F9`
- Manifest SHA-256: `B7C8A2269B286DAC553CB1E1FCCDD75C5F48CE4DF4324C21151EF9751F18B2DC`

## File counts

- Manifest payload inventory: 124 files
- Archive listing: 125 files
- Difference: 1 file, the manifest itself, which is included in the archive but excluded from its payload inventory to avoid a self-referential hash entry.
- Expected worktree payload: 124 files
- Archive contains `recovery-manifest.md`: yes
- Archive contains `t -q`: yes
- Archive contains `ulpf`: yes
- Archive contains `.git`: no

## Verification result

PASS. Every one of the 124 manifest payload entries was verified against the current path, byte size, and SHA-256 hash before archive creation. The archive was listed with `tar -tf`; its 125 file entries equal the 124 payload files plus the manifest. The required `ulpf` tree and `t -q` are present. No source files, tests, existing artifacts, or Git history were modified, removed, moved, reverted, overwritten, or reformatted.

## Test evidence preserved in manifest

- Focused regression: 18 passed
- Full regression: 91 passed
- Diff check: passed
- Failures/errors/skips: 0/0/0
- Pytest warnings: 0

This report records verification only. It does not authorize cleanup, Git mutation, implementation separation, commits, or Phase 2 work.
