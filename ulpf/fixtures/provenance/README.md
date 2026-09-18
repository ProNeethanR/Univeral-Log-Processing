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
| cef-real-001 | fixtures/raw/cef/cef-real-001.log                      | cef    | real           | 1     | 755326d148ce3f2c…       | 1628  |
| (reference)  | fixtures/raw/cef/doc_reference/cef-doc-examples.log    | cef    | docs-only      | 10    | b80b3a483c6a0a91…       | 1095  |

**cef-real-001 Source**: Palo Alto Networks Cortex XDR output posted in
Grafana Loki GitHub Issue #5648 — confirmed real product output.  
**SHA-256**: `755326d148ce3f2c456c79c97bec6a6b9981f1a8b3450c2588b5a66c87cf79ad`  
**Bytes**: 1628  
**License**: Public GitHub issue comment — implied acceptable for test use;
no explicit licence grant. Decision on redistribution deferred.

> ⚠️ **CEF Limitation**: CEF currently consists of only 1 real sample.
> This is insufficient for statistical validation. Parser tests against CEF
> will be treated as smoke tests only until additional real CEF fixtures are
> acquired during the validation phase.

**cef-doc-examples Source**: Manually constructed from vendor documentation
(Palo Alto, Fortinet, Check Point reference guides). **NOT** real captures.  
**SHA-256**: `b80b3a483c6a0a91b1193c9d6c3b2fe9fed58d0f1ee8715ac29fee181ea4e3bc`  
**Bytes**: 1095  
**License**: Derived from public vendor documentation. Not for redistribution.

**Excluded source (negative example)**: `alasta/splunkdemo fortigate.log` —
verbatim match to Fortinet documentation examples (same `eventtime`, same
`sessionid`, same UUIDs as vendor cookbook). Not a real capture. Excluded
from primary fixtures.

---

## Vendor Key-Value Fixtures

| fixture_id    | relative path                           | format    | classification | lines | sha256 (first 16 chars) | bytes |
|---------------|-----------------------------------------|-----------|----------------|-------|-------------------------|-------|
| fortigate-001 | fixtures/raw/vendor/fortigate-001.log   | fortigate | real           | 15    | 162edcbc838ed90c…       | 8905  |

**Source**: `santiago-bassett/Alienvault-Demo_scripts` — confirmed real
device identifier `devid=FG200B3910602686`, `devname=JLL_FW`.  
**SHA-256**: `162edcbc838ed90c1bad712fc485977e43225e1b6ccf715adb0ee7eb1ae00caf`  
**Bytes**: 8905  
**License**: No LICENSE file in the repository — default copyright applies.
Decision on redistribution deferred.
