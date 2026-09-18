# Outcome Definitions

These are the **only four** status values permitted in all ULPF parser tests,
validation reports, and CI output. No other terms (e.g. "partial", "skipped",
"error", "n/a") are valid outcome labels.

---

## `resolved`

The source field was successfully extracted from the raw log, its semantic
meaning was confirmed against the fixture's ground-truth annotation, and the
value was mapped to a **concrete, named attribute** in the OCSF 1.3.0 schema.

A field is `resolved` only when:
- The field name was present in the raw log.
- The ground-truth file confirmed its meaning (not marked `unknown`).
- The parser produced an output value at the correct OCSF path.
- The value type matches the OCSF-declared type for that attribute.

---

## `unknown`

The field is **present in the raw log** but no mapping rule exists for it
yet in the current parser version. The field has been observed but not yet
assigned a semantic meaning or OCSF target.

`unknown` is distinct from `unmapped`: the difference is intent. An `unknown`
field is a gap — it may be resolvable in a future parser version once the
meaning is established.

---

## `unmapped`

The field is present in the raw log and its semantic meaning is understood,
but it has been **intentionally excluded** from OCSF mapping. This status
is used for:
- Vendor-specific noise fields with no OCSF equivalent (e.g. internal
  session counters, proprietary flags).
- Fields that are redundant given other already-resolved fields.
- Fields the project has explicitly decided not to surface.

`unmapped` is a deliberate decision, not a gap. It must be documented in
the ground-truth annotation with a reason.

---

## `invalid`

The field is present in the raw log and a mapping rule exists, but the
extracted value **fails validation**. Causes include:
- Wrong data type (e.g. a non-numeric value in an integer field).
- Out-of-range value (e.g. port number > 65535, severity > 10 for CEF).
- Malformed value (e.g. an IP address that fails RFC 791 format check,
  a timestamp that cannot be parsed by the declared format).
- A value that violates an OCSF enumeration constraint.

An `invalid` field is extracted but not written to the OCSF output.
It must be surfaced in the parser's validation report.

---

## Summary Table

| Status     | Present in raw | Meaning known | Mapping rule exists | Value passes validation |
|------------|----------------|---------------|---------------------|------------------------|
| `resolved` | ✓              | ✓             | ✓                   | ✓                      |
| `unknown`  | ✓              | ✗             | ✗                   | —                      |
| `unmapped` | ✓              | ✓             | deliberately none   | —                      |
| `invalid`  | ✓              | ✓             | ✓                   | ✗                      |
