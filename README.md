# ULPF — Universal Log Processing Framework

A log processing pipeline that takes raw enterprise logs (Syslog, CEF, vendor formats), parses them with a YAML-based DSL, normalizes them to [OCSF 1.3.0](https://schema.ocsf.io/), and stores everything in a tamper-evident vault. The whole thing runs offline — no cloud dependencies, no external schema fetches.

It ships with a FastAPI backend and a self-contained web dashboard for exploring events, verifying integrity chains, testing parsers, and monitoring pipeline health.

## What it does

- **Parses logs with YAML rules** — declarative parser definitions in `parsers/*.yaml` extract structured fields from raw text. No arbitrary code execution.
- **Validates against OCSF 1.3.0** — every normalized event is validated against a local frozen copy of the OCSF schema. The validator checks the schema's SHA-256 hash on startup, so you know it hasn't been tampered with.
- **Stores raw logs in a vault** — raw bytes go into an append-only store with SHA-256 digests and chain verification. Even after retention purge, tombstone metadata keeps the chain verifiable.
- **Quarantines bad events** — anything that fails parsing or schema validation gets quarantined with a failure record. No raw payload leakage.
- **Manages source profiles** — versioned registry for parser + source context lifecycle (draft → active → deprecated). Persisted to disk.

## Architecture

```
                       +-------------------------+
                       |     Raw Log Streams     |
                       +-------------------------+
                                    |
                                    v
+------------------+      +-------------------+      +-------------------+
|  Raw Log Vault   | <--- | Ingestion Engine  | ---> |  Source Registry  |
| (SHA-256 Store)  |      +-------------------+      +-------------------+
+------------------+                |                          |
                                    v                          v
                          +-------------------+      +-------------------+
                          |  DSL Interpreter  | <--- |   YAML DSL Def    |
                          +-------------------+      +-------------------+
                                    |
                                    v
                          +-------------------+
                          |    OCSF Mapper    |
                          +-------------------+
                                    |
                                    v
                          +-------------------+
                          | OCSF 1.3.0       |
                          | Runtime Validator | (Offline)
                          +-------------------+
                                    |
                                    v
                          +-------------------+
                          |   Trust Gate      |
                          +-------------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+-----------------------+                       +-----------------------+
|  Validated OCSF Event |                       |  Quarantine Record    |
+-----------------------+                       +-----------------------+
            \                                               /
             +---------------------------------------------+
                                    |
                                    v
       +---------------------------------------------------------+
       |              FastAPI Backend (src/api)                  |
       +---------------------------------------------------------+
                                    |
                                    v
       +---------------------------------------------------------+
       |           Web Dashboard (src/api/static)                |
       | Overview | Events | Vault | Quarantine | Sources |      |
       | Plugins | Benchmark | Ingest Tester | Studio | Runs    |
       +---------------------------------------------------------+
```

## Project layout

```
├── contracts/                  # JSON Schema contracts for envelopes, parsers, source context
├── docs/                       # Architecture docs, hardening notes
├── fixtures/
│   ├── raw/                    # Sample logs (syslog, CEF, fortigate, demo)
│   ├── ground_truth/           # Expected normalized outputs
│   ├── provenance/             # Where each fixture came from
│   ├── manifest.json           # Fixture tracking
│   └── SHA256SUMS              # Hash verification
├── parsers/
│   └── syslog.yaml             # Syslog parser definition (DSL)
├── schema/
│   └── ocsf/ocsf_schema.json   # Frozen OCSF 1.3.0 schema
├── src/
│   ├── api/                    # FastAPI app
│   │   ├── main.py             # Routes, lifespan, static mount
│   │   ├── models.py           # Pydantic models
│   │   ├── services/           # Event, run, quarantine logic
│   │   └── static/             # Frontend SPA (HTML + JS + CSS)
│   ├── ingestion/ingestor.py   # Raw log capture
│   ├── normalization/
│   │   ├── mapper.py           # OCSF field mapping + context injection
│   │   └── ocsf_validator.py   # Offline schema validator
│   ├── parsers/
│   │   ├── interpreter.py      # DSL execution engine
│   │   ├── engine.py           # Parser interface
│   │   └── dsl_validator.py    # DSL syntax checks
│   ├── registry/__init__.py    # Source profile + parser registry
│   └── vault/store.py          # Append-only vault, chain, checkpoints
├── tests/                      # 206 tests across all modules
├── demo.py                     # CLI demo script
└── requirements.txt
```

## Setup

**Requirements:** Python 3.10+, a modern browser. No Node.js needed — the frontend is vanilla HTML/CSS/JS served by FastAPI.

```bash
git clone https://github.com/ProNeethanR/Univeral-Log-Processing.git
cd Univeral-Log-Processing

python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Linux / macOS
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

## Running it

### Backend + Frontend (single process)

The backend serves both the API and the dashboard. One command, one process:

```powershell
# Windows PowerShell
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```

```bash
# Linux / macOS
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```

On server startup, the dashboard initializes in a clean genesis / nil state. Then open:

| URL | What |
|---|---|
| `http://127.0.0.1:8000` | Web dashboard |
| `http://127.0.0.1:8000/docs` | Swagger API docs |

Click the **"Run Pipeline"** button in the top navigation bar to trigger live ingestion, cryptographic vault anchoring, DSL parsing, and OCSF 1.3.0 schema validation across all fixtures.

### CLI demo (no server needed)

```bash
python demo.py
```

Runs the full pipeline end-to-end in your terminal: registers a source profile, ingests syslog events, parses them, maps to OCSF, validates, and prints the results.

## Frontend — Dashboard Views

The unified responsive dashboard features 8 core operational views:

| Tab | What it shows |
|---|---|
| **Overview** | Interactive 6-stage DAG architecture, live telemetry KPIs (Ingested, OCSF Pass Rate, Diverted), and TPM-anchored Merkle root status |
| **Events** | Searchable OCSF event ledger with multi-column filters. Click "Inspect →" to review raw evidence, parsed dict, OCSF JSON, and strict schema validation reports |
| **Vault** | Cryptographic hash chain ledger, SHA-256 digests, block locators, genesis checkpoint status, and tamper-detection reports |
| **Quarantine** | Dead-Letter Queue (DLQ) with categorical isolation (schema violations, missing context). Features an active **"Reprocess Quarantined"** action button |
| **Sources** | Active registered source profiles and enterprise connector telemetry (Cisco ASA, Palo Alto, Fortinet, Netfilter) with protocol details and EPS |
| **Plugins** | Sandboxed parser plugin catalog (AST YAML DSL and WASM enclaves) with hot-reload actions and latency metrics |
| **Benchmark** | Dynamic synthetic load generator with multi-profile simulations (Mixed Enterprise, Syslog RFC 5424, CloudTrail, Cisco ASA) and live SVG latency graphs |
| **Ingest Tester** | Live multi-format parser tester: paste raw logs from any system (Syslog, Windows Event XML, Apache, DNS, Postfix) to view detected tokens and mapped fields |

The header bar features a prominent **"Run Pipeline"** button to dispatch end-to-end runs and a live **Chain Integrity Status** indicator.

## Testing

```bash
# Full suite (206 tests)
python -m pytest -v

# Just the demo pipeline integration
python -m pytest tests/integration/test_syslog_demo_pipeline.py -v

# Vault integrity tests
python -m pytest tests/vault/ -v

# Registry + source profile lifecycle
python -m pytest tests/registry/ -v

# Context injection + timezone handling
python -m pytest tests/normalization/test_context_injection.py -v
```

## API quick reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/summary` | Dashboard summary metrics |
| GET | `/api/events` | Paginated event list (supports `search`, `format`, `status`, `validation_status` params) |
| GET | `/api/events/{id}` | Single event detail |
| GET | `/api/events/{id}/raw` | Raw log bytes |
| GET | `/api/events/{id}/parsed` | Parsed field dictionary |
| GET | `/api/events/{id}/normalized` | OCSF normalized event |
| GET | `/api/events/{id}/validation` | Validation result |
| GET | `/api/events/{id}/envelope` | Cryptographic envelope |
| GET | `/api/integrity/verify` | Chain verification report + checkpoint anchor |
| POST | `/api/integrity/checkpoint` | Create chain checkpoint |
| GET | `/api/quarantine` | Failure records (supports `category`, `event_id` filters) |
| GET | `/api/runs` | Pipeline run history |
| GET | `/api/runs/{id}` | Single run detail |
| GET | `/api/runs/{id}/events` | Events within a specific run |

## Code examples

### Validate an OCSF event

```python
from src.normalization.ocsf_validator import OCSFValidator

validator = OCSFValidator()
result = validator.validate({
    "class_uid": 4001,
    "category_uid": 4,
    "activity_id": 1,
    "type_uid": 400101,
    "time": 1726700000,
    "severity_id": 1,
    "metadata": {"version": "1.3.0", "product": {"vendor_name": "ULPF"}},
    "dst_endpoint": {"ip": "192.168.1.100"}
})

if result.is_valid:
    print(f"Valid OCSF {result.ocsf_version} event ({result.class_name})")
else:
    for err in result.errors:
        print(f"  [{err.error_type}] {err.path}: {err.message}")
```

### Parse a raw log

```python
from src.registry import register_parser, _clear_registry
from src.parsers.engine import ParserEngine

_clear_registry()
register_parser("syslog-demo-001", "1.0.0", "parsers/syslog.yaml")

engine = ParserEngine("syslog-demo-001", "1.0.0")
fields = engine.parse(
    "Sep  1 10:00:01 demo-fw kernel: INBOUND TCP: IN=eth0 OUT=eth1 "
    "SRC=203.0.113.10 DST=192.168.1.5 PROTO=TCP SPT=54321 DPT=443"
)
print(fields["SRC"], fields["DST"], fields["DPT"])
```

## Schema integrity

The OCSF schema is pinned to version 1.3.0 and frozen locally. The validator checks its SHA-256 hash on startup:

```
6ccff0f70b6216abc8f82be3756a9a167662a535c64a6a60df111b0db363e3e2
```

You can verify manually:

```bash
python -c "import hashlib; print(hashlib.sha256(open('schema/ocsf/ocsf_schema.json','rb').read()).hexdigest())"
```

If the hash doesn't match, the validator refuses to start. The framework never makes network requests — everything runs from disk.

## Context integrity policy

Source context fields (capture year, timezone, vendor name, product name) are never guessed or inferred. If a real log fixture doesn't have authoritative provenance for these fields, the pipeline honestly fails validation rather than substituting plausible-but-unverified defaults.

## License

Private / Confidential (ULPF Project). See `fixtures/manifest.json` and `fixtures/provenance/` for fixture origins.
