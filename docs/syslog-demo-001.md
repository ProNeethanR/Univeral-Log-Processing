# ULPF Demo Fixture — `syslog-demo-001`

## Overview

`syslog-demo-001` is a **synthetic** RFC3164 Syslog fixture created specifically for the
Universal Log Pre-processing Framework (ULPF) Smart India Hackathon (SIH) demonstration.

It demonstrates the complete, end-to-end ULPF pipeline resulting in a validated OCSF 1.3.0
Network Activity event.

---

## Key Facts

| Property | Value |
|---|---|
| `fixture_id` | `syslog-demo-001` |
| `classification` | `synthetic-demo` |
| `format` | RFC3164 Syslog (Linux `iptables` kernel) |
| Events | 7 |
| `source_profile` | `syslog-demo-001:1.0.0` |
| `capture_year` | 2026 |
| `capture_timezone` | UTC |
| `vendor_name` | Linux |
| `product_name` | iptables |
| OCSF version | 1.3.0 |
| OCSF validation | **PASS** |

> **`syslog-demo-001` is NOT the historical `syslog-001` dataset.**
> Its source context is intentionally complete for demonstration.
> See [Distinction from `syslog-001`](#distinction-from-syslog-001) below.

---

## Complete ULPF Pipeline Demonstration

```
Raw Fixture (7 RFC3164 lines)
    ↓
[Ingestion]      Raw bytes captured, SHA-256 computed, vault locator assigned
    ↓
[Syslog Detection]  Format detected: RFC3164 / iptables
    ↓
[Parsing]        ParserEngine (parsers/syslog.yaml)
                 Extracts: month, day, time, host, SRC, DST, PROTO, ports, etc.
    ↓
[Source Context Injection]   syslog-demo-001:1.0.0 resolved from registry
                             capture_year  = 2026       ← from Source Profile
                             capture_timezone = UTC     ← from Source Profile
                             vendor_name = Linux        ← from Source Profile
                             product_name = iptables    ← from Source Profile
    ↓
[Timestamp Normalization]   RFC3164 month+day+time + capture_year + capture_timezone
                            → deterministic UTC epoch timestamp
    ↓
[OCSF 1.3.0 Mapping]       class_uid=4001 (Network Activity)
                            category_uid=4, activity_id=6, type_uid=400106
                            severity_id=1 (Informational, ULPF policy default)
    ↓
[OCSF 1.3.0 Validation]    ✅ PASS — all required fields present
    ↓
[Provenance]                injected_fields records which fields came from Source Profile
                            policy_fields records OCSF structural constants
    ↓
[Vault Integrity]           SHA-256 verified, chain integrity verified
                            profile_version persisted in vault metadata
```

---

## Source Profile Values and Their Scope

```json
{
  "source": "syslog-demo-001",
  "profile_version": "1.0.0",
  "capture_year": 2026,
  "capture_timezone": "UTC",
  "vendor_name": "Linux",
  "product_name": "iptables"
}
```

**These values apply ONLY to `syslog-demo-001`.**

They are **demo-authored** values for synthetic demonstration data. They are **not**:
- Authoritative metadata for the historical `syslog-001` dataset
- Applicable to any real, unverified log capture

---

## Distinction from `syslog-001`

`syslog-001` is a **real historical fixture** from the Honeynet Project SotM30 (February 2004).

It is intentionally **unregistered** because no authoritative source context has been
established for it. This demonstrates the ULPF framework's honesty principle:

> The ULPF framework refuses to fabricate values. If `capture_year`, `capture_timezone`,
> `vendor_name`, or `product_name` cannot be established authoritatively, they are not used.

`syslog-001` intentionally produces an OCSF validation **FAIL** to demonstrate this behavior.
`syslog-demo-001` intentionally produces an OCSF validation **PASS** to demonstrate what a
complete, authoritative pipeline looks like.

Both are correct and expected behaviors of the framework.

---

## Replay Support

After all 7 demo events are normalized, historical replay is demonstrated by:

1. Deactivating `syslog-demo-001:1.0.0` from the active registry
2. Confirming normal ingestion lookup rejects it (`ProfileInactiveError`)
3. Using `get_historical_source_profile("syslog-demo-001", "1.0.0")` to retrieve the profile
4. Re-normalizing via `OCSFMapper.replay_syslog()` — producing identical output

This demonstrates that the ULPF replay path is independent of the currently active profile.

---

## Running the Demo Test

```bash
python -m pytest tests/integration/test_syslog_demo_pipeline.py -v
```

Expected: **9 passed, 0 failed**.

To run the full regression including historical `syslog-001` tests:

```bash
python -m pytest -q
```

Expected: all tests pass. `syslog-001` OCSF validation continues to assert FAIL (correct).

---

## File Locations

| File | Description |
|---|---|
| `fixtures/raw/syslog/syslog-demo-001.log` | Synthetic raw RFC3164 log (7 events) |
| `fixtures/ground_truth/syslog/syslog-demo-001.json` | Manually authored OCSF ground truth |
| `fixtures/provenance/syslog-demo-001-provenance.md` | Detailed provenance and authoring notes |
| `tests/integration/test_syslog_demo_pipeline.py` | Integration test (9 test cases) |

---

*This document describes the synthetic demo fixture only. It does not describe or modify `syslog-001`.*
