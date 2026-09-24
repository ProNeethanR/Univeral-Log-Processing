# Fixture Provenance

OCSF target version: **1.3.0** (frozen 2026-09-18, see `schema/OCSF_VERSION.md`)

All raw fixtures below have been verified: each entry records the
classification, line count, SHA-256 digest, and byte length of the file on
disk at the time of freezing.

---

## Syslog Fixtures

| fixture_id  | relative path                          | format  | classification | lines | sha256 (first 16 chars) | bytes |
|-------------|----------------------------------------|---------|----------------|-------|-------------------------|-------|
| syslog-001  | fixtures/raw/syslog/syslog-001.log     | syslog  | real           | 25    | a3783b7c387f7248…       | 5330  |

**Source**: Honeynet Project SotM30 — real iptables firewall traffic captured
from a live GenII honeynet in February 2004.
**MD5 of original gzip**: `8c0070ef51f6f764fde0551fa60da11b`
**SHA-256**: `a3783b7c387f7248d8c90c315b9b06a73bf4f7e6d0a6631b0a2449afd5706552`
**Bytes**: 5330
**License**: No explicit license found — used for non-commercial evaluation only.

---

## CEF Fixtures

| fixture_id   | relative path                                          | format | classification | lines | sha256 (first 16 chars) | bytes |
|--------------|--------------------------------------------------------|--------|----------------|-------|-------------------------|-------|
| cef-real-001 | fixtures/raw/cef/cef-real-001.log                      | cef    | real           | 1     | ca37d406d7d67ecf…       | 1629  |
| (reference)  | fixtures/raw/cef/doc_reference/cef-doc-examples.log    | cef    | docs-only      | 10    | bf84db1e910664e5…       | 1105  |

**cef-real-001 Source**: Palo Alto Networks Cortex XDR output posted in
Grafana Loki GitHub Issue #5648 — confirmed real product output.
**SHA-256**: `ca37d406d7d67ecfcd864ef0864a7a3727f8f947ad9457448c97c9d5b46608b1`
**Bytes**: 1629
**License**: Public GitHub issue comment — implied acceptable for test use;
no explicit licence grant. Decision on redistribution deferred.

> ⚠️ **CEF Limitation**: CEF currently consists of only 1 real sample.
> This is insufficient for statistical validation. Parser tests against CEF
> will be treated as smoke tests only until additional real CEF fixtures are
> acquired during the validation phase.

**cef-doc-examples Source**: Manually constructed from vendor documentation
(Palo Alto, Fortinet, Check Point reference guides). **NOT** real captures.
**SHA-256**: `bf84db1e910664e548bc71952fd4699ce497ad9ea4a4e9926462fd18af6826df`
**Bytes**: 1105
**License**: Derived from public vendor documentation. Not for redistribution.

**Excluded source (negative example)**: `alasta/splunkdemo fortigate.log` —
verbatim match to Fortinet documentation examples (same `eventtime`, same
`sessionid`, same UUIDs as vendor cookbook). Not a real capture. Excluded
from primary fixtures.

---

## Vendor Key-Value Fixtures

| fixture_id    | relative path                           | format    | classification | lines | sha256 (first 16 chars) | bytes |
|---------------|-----------------------------------------|-----------|----------------|-------|-------------------------|-------|
| fortigate-001 | fixtures/raw/vendor/fortigate-001.log   | fortigate | real           | 15    | 21a07d34ce4ba023…       | 8926  |

**Source**: `santiago-bassett/Alienvault-Demo_scripts` — confirmed real
device identifier `devid=FG200B3910602686`, `devname=JLL_FW`.
**SHA-256**: `21a07d34ce4ba0235ea2678bb5ec682dbba0c39cb936f9cdca5772146beaec2f`
**Bytes**: 8926
**License**: No LICENSE file in the repository — default copyright applies.
Decision on redistribution deferred.
