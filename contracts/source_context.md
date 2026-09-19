# ULPF Source Context Architecture Contract

## Overview
This document defines the architectural decisions and contracts for providing Source Context to the ULPF pipeline. Source Context refers to the metadata required to deterministically parse and normalize logs that cannot be inferred from the raw payloads (e.g. capture year, capture timezone, vendor identity).

## Conceptual Model

The pipeline requires three distinct identities to deterministically process an event:
1. **Parser Version**: The version of the parsing rules logic.
2. **Source Profile Version**: The version of the context metadata (year, timezone, vendor).
3. **OCSF Schema Version**: The output schema version (currently frozen at 1.3.0).

These must not be conflated.

## Timestamp Semantics
* **Timestamp Source**: Extracted from the raw log via parser instructions.
* **Year Source**: Must be provided by the Source Profile `capture_year`.
* **Timezone Source**: Must be provided by the Source Profile `capture_timezone`.
* **Parsing Semantics**: The pipeline must parse the timestamp from the log and augment it with the `capture_year` and `capture_timezone` strictly from the Source Profile.
* **Failure behavior**: If year or timezone are missing from the Source Profile, execution must fail-closed (explicit error).
* **FORBIDDEN Fallbacks**:
  - Current year fallback is **FORBIDDEN**.
  - System/local timezone fallback is **FORBIDDEN**.
  - UTC fallback (unless explicitly defined as the capture timezone) is **FORBIDDEN**.
  - The system clock is NEVER consulted during runtime parsing.

## OCSF Metadata Mapping
Based on OCSF 1.3.0:
* `metadata.product.vendor_name` is **REQUIRED**. Must be supplied by Source Profile `vendor_name`.
* `metadata.product.name` is **RECOMMENDED** in OCSF, but the ULPF Source Profile contract declares it explicitly required in the profile to ensure rich identity mapping. Must be supplied by Source Profile `product_name`.

## Fixture Semantics Decision
* The `fixtures/expected/` files are intended to represent the **final validated OCSF output**.
* The current `syslog-001` expected fixture does not contain the mandatory `metadata` chain.
* **Decision**: Fixtures must eventually be upgraded to represent valid OCSF 1.3.0 output, but this modification belongs to a later fixture migration step, NOT the Source Context implementation.

## Decision Matrix

| Decision                   | Current Evidence | Proposed Contract | Status        | Owner |
| -------------------------- | ---------------- | ----------------- | ------------- | ----- |
| Source Profile identity    | None             | `(source, profile_version)` | RESOLVED | Architecture Lead |
| Source Profile schema      | None             | `source_context.schema.json` | RESOLVED | Architecture Lead |
| Registry ownership         | None             | Platform Engineering | RESOLVED | Platform Engineering |
| Registry resolution API    | Empty file       | API defined in `registry_api.md` | RESOLVED | Platform Engineering |
| Replay identity            | None             | Must supply original `profile_version` | RESOLVED | Architecture Lead |
| capture_year authority     | None             | Source Profile `capture_year` | RESOLVED | Architecture Lead |
| capture_timezone authority | None             | Source Profile `capture_timezone` | RESOLVED | Architecture Lead |
| vendor_name authority      | None             | Source Profile `vendor_name` | RESOLVED | Architecture Lead |
| product_name authority     | None             | Source Profile `product_name` | RESOLVED | Architecture Lead |
| timestamp semantics        | None             | No fallback. Fail-closed. | RESOLVED | Architecture Lead |
| fixture semantics          | Expected invalid | Upgrade in future step | RESOLVED | QA/Testing Lead |
