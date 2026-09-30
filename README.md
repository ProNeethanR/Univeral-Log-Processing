# Universal Log Processing Framework (ULPF)

**Universal Log Processing Framework (ULPF)** is a deterministic, high-assurance log processing and normalization architecture. It ingests raw, heterogeneous enterprise log streams (Syslog, CEF, vendor formats), stores them in a tamper-evident vault, extracts structured fields using a declarative DSL interpreter, and validates normalized events against the frozen **OCSF (Open Cybersecurity Schema Framework) 1.3.0** standard completely offline.

The platform includes a built-in, pixel-perfect **Web Dashboard (Frontend)** and **FastAPI Service (Backend)** for real-time log exploration, cryptographic chain verification, DSL parser authoring, and quarantine triage.

---

## 🚀 Key Features

* **Deterministic DSL-Driven Parsing Engine**: Executes declarative YAML parser rules to parse, tokenize, and transform raw unformatted logs into structured JSON without arbitrary code execution.
* **Air-Gapped OCSF 1.3.0 Runtime Validator**: Validates candidate normalized events strictly against a local, frozen OCSF 1.3.0 schema artifact (`schema/ocsf/ocsf_schema.json`). Works 100% offline without remote network schema lookups.
* **Cryptographic Schema Integrity**: Automatically verifies the SHA-256 checksum (`6ccff0f70b6216abc8f82be3756a9a167662a535c64a6a60df111b0db363e3e2`) and version (`1.3.0`) of the frozen OCSF schema upon initialization.
* **Tamper-Evident Raw Log Vault**: Stores raw unparsed logs with SHA-256 payload digests, byte-range metadata, and an append-only integrity chain. Retention purge keeps a metadata tombstone so historical chain verification survives ordinary expiry.
* **Lossless Byte-Level Capture**: Raw records are captured as exact original byte slices (terminators included) before any decoding or parsing; offsets are integrity-protected metadata.
* **Checkpoint-Anchored Verification**: `GET /api/integrity/verify` reports chain state plus an explicit checkpoint anchor (`valid`/`missing`/`stale`/`invalid`); overall `verified` requires a valid anchor on the current head (`POST /api/integrity/checkpoint`).
* **Trust Gate & Quarantine**: Envelopes carry a `trusted` flag (validated evidence + verified integrity); rejected events and integrity anomalies are recorded as raw-content-free failure records queryable at `GET /api/quarantine`.
* **Dynamic & Persistent Source Profile Registry**: Versioned registry supporting parser and source context lifecycle management (draft, active, deprecated, historical replay) with durable file persistence.
* **Integrated Enclave Web Dashboard (Frontend)**: Native, zero-dependency SPA (HTML5, custom CSS design tokens, Vanilla JS) served directly by FastAPI. Provides 6 purpose-built operator views: Overview, Events, Vault, Quarantine, Studio, and Runs.

---

## 🏗️ System Architecture

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
                          |  OCSF 1.3.0       |
                          |  Runtime Validator| (Offline Verification)
                          +-------------------+
                                    |
                                    v
                          +-------------------+
                          | Trust Gate / Env  |
                          +-------------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+-----------------------+                       +-----------------------+
|  Validated OCSF Event |                       |  Quarantine Failure   |
+-----------------------+                       +-----------------------+
            \                                               /
             \                                             /
              v                                           v
       +---------------------------------------------------------+
       |           FastAPI REST Backend (src/api)               |
       +---------------------------------------------------------+
                                    |
                                    v
       +---------------------------------------------------------+
       |      Web Dashboard Frontend (src/api/static)           |
       |   Overview | Events | Vault | Quarantine | Studio | Runs|
       +---------------------------------------------------------+
```

---

## 📁 Repository Structure

```
Univeral-Log-Processing/
├── contracts/                  # Schema definitions & event contract specification
│   ├── event_contract.schema.json   # Canonical envelope contract (schema_version 1.1)
│   ├── failure_record.schema.json   # Quarantine failure record contract
│   ├── parser_mapping.schema.json   # DSL parser grammar & operator contract
│   └── source_context.schema.json   # Authoritative source context contract
├── docs/
│   ├── architecture.md              # Implemented-system architecture & runtime contracts
│   ├── phase6-completion-hardening.md  # Hardening pass: design decisions & coverage
│   └── syslog-demo-001.md           # Synthetic demo pipeline documentation
├── fixtures/                   # Ground-truth evaluation & raw log test fixtures
│   ├── ground_truth/           # Pre-authored expected normalized ground truths
│   ├── raw/                    # Raw sample logs (Syslog, CEF, Fortigate, Demo)
│   ├── provenance/             # Fixture origins and authoring notes
│   ├── manifest.json           # Fixture tracking manifest
│   └── SHA256SUMS              # Hash verification for raw fixtures
├── parsers/                    # Declarative YAML DSL parser definitions
│   └── syslog.yaml             # Example Syslog parser definition
├── schema/                     # OCSF schema artifacts and version freezes
│   ├── ocsf/
│   │   ├── ocsf_schema.json    # Frozen OCSF 1.3.0 exported schema
│   │   └── README.md           # Schema acquisition metadata
│   └── OCSF_VERSION.md         # OCSF version freeze declaration
├── src/                        # Core Python application packages
│   ├── api/                    # FastAPI backend & web services
│   │   ├── main.py             # ASGI entrypoint, routing & static file mount
│   │   ├── models.py           # Envelope, trust gate, failure record models
│   │   ├── services/           # Event, run, and quarantine services
│   │   └── static/             # Web Dashboard (Frontend)
│   │       ├── index.html      # Single Page Application container
│   │       ├── app.js          # Dashboard state & view controller
│   │       ├── style.css       # Layout & view-specific component styles
│   │       └── tokens.css      # Design token system (colors, typography, spacing)
│   ├── ingestion/              # Ingestor pipeline & raw ref generator
│   │   └── ingestor.py
│   ├── normalization/          # OCSF mapper & runtime validator
│   │   ├── mapper.py           # Field normalization mapper & context injection
│   │   └── ocsf_validator.py   # Air-gapped OCSF 1.3.0 validator
│   ├── parsers/                # DSL parsing engine & interpreter
│   │   ├── dsl_validator.py    # DSL syntax validator
│   │   ├── engine.py           # High-level parser engine interface
│   │   ├── exceptions.py       # Custom framework exception definitions
│   │   └── interpreter.py      # Core DSL execution engine
│   ├── registry/               # Source Profile & Parser Registry
│   │   └── __init__.py         # Durable file storage, versioning, reload, replay
│   └── vault/                  # Raw log content-addressable storage
│       └── store.py            # Chain, retention tombstones, checkpoints
├── tests/                      # Framework test suites (206 tests)
│   ├── integration/            # Pipeline, demo, & API integration tests
│   ├── ingestion/              # Lossless capture tests
│   ├── normalization/          # OCSF validator & context injection tests
│   ├── parsers/                # Interpreter & engine unit tests
│   ├── registry/               # Registry management & persistence tests
│   └── vault/                  # Chain, retention, checkpoint tests
├── demo.py                     # Standalone CLI demo runner
├── requirements.txt            # Python dependencies
└── README.md
```

---

## ⚙️ Prerequisites & Installation

### Requirements

* **Python**: `3.10` or higher
* **Web Browser**: Modern browser (Chrome, Edge, Firefox, Safari)
* **Zero Node.js/NPM Dependency**: The frontend is built with pure Vanilla HTML5/CSS3/ES6 and is served directly by the backend. No build steps or bundlers are required!

### Installation Steps

1. **Clone the repository**:

   ```bash
   git clone https://github.com/ProNeethanR/Univeral-Log-Processing.git
   cd Univeral-Log-Processing
   ```

2. **Set up a Virtual Environment (Recommended)**:

   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

---

## 🌐 Running the Backend & Web Dashboard (Frontend)

ULPF uses a unified single-process architecture: the FastAPI backend serves both the REST API endpoints and mounts the frontend dashboard at the root URL.

### 1. Launch with Demo Data Pre-loaded (Recommended for Evaluation)

Setting `ULPF_DEMO_DATA=true` automatically loads demo log streams, registers parsers, and creates a demo pipeline run upon server startup:

* **Windows PowerShell**:
  ```powershell
  $env:ULPF_DEMO_DATA="true"; python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
  ```

* **Linux / macOS (Bash)**:
  ```bash
  ULPF_DEMO_DATA=true python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
  ```

* **Windows Command Prompt (CMD)**:
  ```cmd
  set ULPF_DEMO_DATA=true && python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
  ```

### 2. Launch Clean (Without Pre-loaded Demo Data)

```bash
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 🖥️ Exploring the Web Dashboard

Once the server is running, access the following in your web browser:

| Interface | URL | Description |
|---|---|---|
| **ULPF Web Dashboard** | `http://127.0.0.1:8000` | Full visual dashboard (Overview, Events, Vault, Quarantine, Studio, Runs) |
| **Interactive API Docs (Swagger UI)** | `http://127.0.0.1:8000/docs` | Live API playground and schema specifications |
| **Raw OpenAPI JSON** | `http://127.0.0.1:8000/openapi.json` | Machine-readable API definition |

### Dashboard Navigation & Views

1. **Overview**: Displays pipeline health, total ingested logs, parsing/normalization success rates, throughput metrics (EPS), and enclave verification status.
2. **Events**: Real-time event explorer. Supports full-text search, filtering by log format (`syslog`, `cef`), ingestion status, and validation status (`VALID`, `INVALID`). Click any row to slide out the **Event Inspector Drawer** containing:
   * **Raw Log**: Original byte-preserved raw log.
   * **Parsed Fields**: Tokenized key-value dictionary extracted by the DSL.
   * **Normalized OCSF**: JSON event mapped to OCSF 1.3.0 standard.
   * **Validation**: Detailed pass/fail report with exact schema error paths.
   * **Envelope**: Cryptographic provenance envelope with SHA-256 hash and trust state.
3. **Vault**: Content-addressable storage monitor showing tamper-evident SHA-256 digests, byte offsets, anchor states, and cryptographic chain verification.
4. **Quarantine**: Triage area for rejected events and schema anomalies, displaying failure categories without leaking raw sensitive payloads.
5. **Studio**: Interactive DSL authoring sandbox. Test custom YAML parser rules against sample raw logs with live syntax validation and preview.
6. **Runs**: Execution history of log processing batches with per-run stats and event drill-downs.
7. **"Run Demo Pipeline" Action**: Click the button in the top navigation bar at any time to execute the demo pipeline live from the browser.

---

## 🧪 Testing the Project

ULPF provides multiple testing methods: a one-line CLI demo script, targeted integration tests, and the full automated pytest suite.

### 1. Run the Live CLI Demo Script

To see the complete pipeline execute in your terminal with colorful console output and pretty-printed OCSF JSON:

```bash
python demo.py
```

*What this demonstrates:*
* Authoritative Source Profile registration (`syslog-demo-001:1.0.0`)
* Ingestion of synthetic RFC3164 Syslog events
* Declarative parsing using `parsers/syslog.yaml`
* Authoritative context injection (`capture_year=2026`, `capture_timezone=UTC`, `vendor_name=Linux`, `product_name=iptables`)
* **100% OCSF 1.3.0 Validation: PASS** on all events
* Formatted OCSF 1.3.0 event JSON output

### 2. Execute the Full Automated Test Suite (206 Tests)

```bash
python -m pytest -v
```

*Expected output*: All 206 tests passing cleanly (`206 passed`).

### 3. Run Targeted Test Suites

* **Synthetic Demo Pipeline Integration Tests** (9 tests):
  ```bash
  python -m pytest tests/integration/test_syslog_demo_pipeline.py -v
  ```

* **Real Historical Fixture Negative Gate** (verifies honest failure on unverified context):
  ```bash
  python -m pytest tests/integration/test_syslog_pipeline.py -v
  ```

* **Source Profile Persistence & Lifecycle Tests** (28 tests):
  ```bash
  python -m pytest tests/registry/ -v
  ```

* **Timezone & Context Injection Portability Tests** (7 tests):
  ```bash
  python -m pytest tests/normalization/test_context_injection.py -v
  ```

* **Tamper-Evident Vault & Checkpoint Tests**:
  ```bash
  python -m pytest tests/vault/ -v
  ```

### 4. Verify Frozen OCSF 1.3.0 Schema Checksum

Independently verify that the local OCSF schema artifact has not been modified or corrupted:

```bash
python -c "import hashlib; print(hashlib.sha256(open('schema/ocsf/ocsf_schema.json','rb').read()).hexdigest())"
```

*Expected Checksum*:
`6ccff0f70b6216abc8f82be3756a9a167662a535c64a6a60df111b0db363e3e2`

---

## 💻 Programmatic Usage & Examples

### 1. Validating an OCSF Event (Offline Runtime Validator)

The `OCSFValidator` component verifies candidate OCSF event dictionaries completely offline.

```python
from src.normalization.ocsf_validator import OCSFValidator, validate_ocsf_event
from src.parsers.exceptions import OCSFValidationError

# Candidate normalized OCSF event
ocsf_event = {
    "class_uid": 4001,           # Network Activity
    "category_uid": 4,          # Network
    "activity_id": 1,           # Open
    "type_uid": 400101,         # Network Activity: Open
    "time": 1726700000,         # Epoch timestamp
    "severity_id": 1,           # Informational
    "metadata": {
        "version": "1.3.0",
        "product": {
            "vendor_name": "ULPF"
        }
    },
    "dst_endpoint": {
        "ip": "192.168.1.100"
    }
}

# Method A: Structured Validation Result
validator = OCSFValidator()
result = validator.validate(ocsf_event)

if result.is_valid:
    print(f"Event is valid against OCSF {result.ocsf_version} ({result.class_name})")
else:
    print(f"Validation failed with {len(result.errors)} errors:")
    for err in result.errors:
        print(f"   [{err.error_type}] Path: {err.path} -> {err.message}")

# Method B: Raising Exception on Validation Failure
try:
    validate_ocsf_event(ocsf_event, raise_on_error=True)
    print("Event validated successfully!")
except OCSFValidationError as e:
    print(f"Error: {e}")
```

### 2. Parsing Raw Logs with the DSL Engine

```python
from src.registry import register_parser, _clear_registry
from src.parsers.engine import ParserEngine

# Register the shipped syslog parser definition under (source, version)
_clear_registry()
register_parser("syslog-demo-001", "1.0.0", "parsers/syslog.yaml")

# Resolve, contract-validate, and execute
engine = ParserEngine("syslog-demo-001", "1.0.0")
raw_log = "Sep  1 10:00:01 demo-fw kernel: INBOUND TCP: IN=eth0 OUT=eth1 SRC=203.0.113.10 DST=192.168.1.5 PROTO=TCP SPT=54321 DPT=443"
extracted_fields = engine.parse(raw_log)

print(extracted_fields["syslog_month"], extracted_fields["SRC"], extracted_fields["DST"])
```

---

## 🔒 Security & Schema Freeze Policy

1. **OCSF Version Freeze**: The framework is pinned to **OCSF 1.3.0**. Version upgrades require explicit architectural review and update to `schema/OCSF_VERSION.md`.
2. **Air-Gapped Guarantee**: The runtime validator does not make network socket calls, DNS resolutions, or HTTP requests. It operates exclusively from local disk artifacts.
3. **Schema Integrity Safeguard**: If `schema/ocsf/ocsf_schema.json` is modified or tampered with, `OCSFValidator` will fail initialization instantly to prevent downstream invalid mappings.
4. **Honest Context Gate**: Missing capture context (year, timezone, vendor identity) is never fabricated or guessed. Real captures without authoritative parameters are rejected with honest validation failures rather than masked with false defaults.

---

## 📄 License & Provenance

* **Framework License**: Private / Confidential (ULPF Project).
* **Test Fixture Provenance**: Refer to [`fixtures/manifest.json`](file:///d:/sih26/Univeral-Log-Processing/fixtures/manifest.json) and individual provenance files in [`fixtures/provenance/`](file:///d:/sih26/Univeral-Log-Processing/fixtures/provenance/) for complete audit histories of historical and synthetic fixtures.
