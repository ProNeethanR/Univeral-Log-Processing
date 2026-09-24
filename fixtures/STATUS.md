# Fixture Status

Last updated: 2026-09-18

> **2026-09-23 reconciliation (FI-1)**: SHA-256 digests and byte lengths
> below were re-verified against the on-disk (committed) fixture corpus and
> corrected where the 2026-09-18 records were stale. The
> `fixtures/SHA256SUMS`, `fixtures/manifest.json`, and
> `fixtures/provenance/README.md` were regenerated to match the committed
> files, which are authoritative and consistent with `recovery-manifest.md`
> (2026-09-22). The 2026-09-18 digest values for `cef-real-001.log`
> (755326d1…/1628), `cef-doc-examples.log` (b80b3a48…/1095), and
> `fortigate-001.log` (162edcbc…/8905) described pre-edit content and no
> longer match any file in the repository; they are superseded.

---

## OCSF Version

All fixtures and ground-truth files target **OCSF 1.3.0** exclusively.
See `schema/OCSF_VERSION.md` for the freeze statement.

---

## Manifest Consistency

`fixtures/manifest.json` was verified on 2026-09-18.

| fixture_id    | raw_file exists | ground_truth exists | expected exists | status      |
|---------------|-----------------|---------------------|-----------------|-------------|
| syslog-001    | ✓               | ✓                   | ✓               | CONSISTENT  |
| cef-real-001  | ✓               | ✓                   | ✓               | CONSISTENT  |
| fortigate-001 | ✓               | ✓                   | ✓               | CONSISTENT  |

**Broken references**: None.

---

## Ground-Truth Independence

Ground-truth files were authored on **2026-09-18T06:52:56Z** (UTC timestamp
from disk). The parser implementation has not been written yet — no parser
source files exist anywhere in this repository as of this date. The ground-
truth files were therefore produced without running any parser code.

Verification method: filesystem timestamp inspection confirmed all three
ground-truth files (`cef-real-001.json`, `syslog-001.json`,
`fortigate-001.json`) carry the same write time, consistent with a single
authoring session during fixture setup. No `src/parsers/` code existed at
that time.

**Result**: Ground truth was authored before parser implementation and is
therefore established as a pre-implementation baseline. Temporal independence
is confirmed; semantic independence is not claimed from timestamps alone.

---

## CEF Limitation

> ⚠️ **CEF currently consists of only 1 real sample. This is insufficient
> for statistical validation. Parser tests against CEF will be treated as
> smoke tests only until additional real CEF fixtures are acquired during
> the validation phase.**

---

## Fixtures with SHA-256 + Byte Length

All 4 raw fixture files (including the docs-only reference file) have SHA-256
digests and byte lengths recorded in `fixtures/SHA256SUMS` and in
`fixtures/provenance/README.md`.

| file                                              | bytes | sha256 verified |
|---------------------------------------------------|-------|-----------------|
| fixtures/raw/cef/cef-real-001.log                 | 1629  | ✓               |
| fixtures/raw/cef/doc_reference/cef-doc-examples.log | 1105 | ✓              |
| fixtures/raw/syslog/syslog-001.log                | 5330  | ✓               |
| fixtures/raw/vendor/fortigate-001.log             | 8926  | ✓               |

---

## License / Redistribution Decisions Pending

The following sources do not have an explicit open-source license. A decision
is required before any public release or submission of this repository:

1. **syslog-001** — Honeynet Project SotM30 (no explicit license found).
2. **fortigate-001** — `santiago-bassett/Alienvault-Demo_scripts` (no
   `LICENSE` file; default copyright applies).
3. **cef-real-001** — Public GitHub issue comment from Grafana Loki #5648
   (implied acceptable for test use, no explicit grant).
