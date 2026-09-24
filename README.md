# Universal Log Processing Framework (ULPF)

**Universal Log Processing Framework (ULPF)** is a deterministic, high-assurance log processing and normalization architecture. It ingests raw, heterogeneous enterprise log streams (Syslog, CEF, vendor formats), stores them in a tamper-evident vault, extracts structured fields using a declarative DSL interpreter, and validates normalized events against the frozen **OCSF (Open Cybersecurity Schema Framework) 1.3.0** standard completely offline.

---

## 🚀 Key Features

* **Deterministic DSL-Driven Parsing Engine**: Executes declarative YAML parser rules to parse, tokenize, and transform raw unformatted logs into structured JSON without arbitrary code execution.
* **Air-Gapped OCSF 1.3.0 Runtime Validator**: Validates candidate normalized events strictly against a local, frozen OCSF 1.3.0 schema artifact (`schema/ocsf/ocsf_schema.json`). Works 100% offline without remote network schema lookups.
* **Cryptographic Schema Integrity**: Automatically verifies the SHA-256 checksum (`6ccff0f70b6216abc8f82be3756a9a167662a535c64a6a60df111b0db363e3e2`) and version (`1.3.0`) of the frozen OCSF schema upon initialization.
* **Tamper-Evident Raw Log Vault**: Stores raw unparsed logs with SHA-256 payload digests, byte-range metadata, and an append-only integrity chain. Retention purge keeps a metadata tombstone so historical chain verification survives ordinary expiry.
* **Lossless Byte-Level Capture**: Raw records are captured as exact original byte slices (terminators included) before any decoding or parsing; offsets are integrity-protected metadata.
* **Checkpoint-Anchored Verification**: `GET /api/integrity/verify` reports chain state plus an explicit checkpoint anchor (`valid`/`missing`/`stale`/`invalid`); overall `verified` requires a valid anchor on the current head (`POST /api/integrity/checkpoint`).
* **Trust Gate & Quarantine**: Envelopes carry a `trusted` flag (validated evidence + verified integrity); rejected events and integrity anomalies are recorded as raw-content-free failure records queryable at `GET /api/quarantine`.
* **Dynamic Parser Registry**: Versioned registry supporting parser lifecycle management (draft, active, deprecated).

---

## 🏗️ System Architecture

```
                       +-------------------------+
                       |     Raw Log Streams     |
                       +-------------------------+
                                    |
                                    v
+------------------+      +-------------------+      +-------------------+
|  Raw Log Vault   | <--- | Ingestion Engine  | ---> |  Parser Registry  |
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
                       +-------------------------+
                       | Valid Normalized Event  |
                       +-------------------------+
```

---

## 📁 Repository Structure

```
Univeral-Log-Processing/
├── contracts/                  # Schema definitions & event contract specification
│   ├── event_contract.schema.json   # Canonical envelope contract (schema_version 1.1)
│   └── failure_record.schema.json   # Quarantine failure record contract
├── docs/
│   ├── architecture.md              # Implemented-system architecture & runtime contracts
│   └── phase6-completion-hardening.md  # Hardening pass: design decisions & coverage
├── fixtures/                   # Ground-truth evaluation & raw log test fixtures
│   ├── ground_truth/           # Expected normalized ground truth outputs
│   ├── raw/                    # Raw sample logs (Syslog, CEF, Fortigate)
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
│   ├── api/                    # FastAPI dashboard API
│   │   ├── main.py             # Endpoints incl. integrity/checkpoint & quarantine
│   │   ├── models.py           # Envelope, trust gate, failure record models
│   │   └── services/
│   │       ├── event_service.py      # Demo/pipeline event service
│   │       └── quarantine_service.py # In-memory failure record store
│   ├── ingestion/              # Ingestor pipeline & raw ref generator
│   │   └── ingestor.py
│   ├── normalization/          # OCSF mapper & runtime validator
│   │   ├── mapper.py           # Field normalization mapper
│   │   └── ocsf_validator.py   # Air-gapped OCSF 1.3.0 validator
│   ├── parsers/                # DSL parsing engine & interpreter
│   │   ├── dsl_validator.py    # DSL syntax validator
│   │   ├── engine.py           # High-level parser engine interface
│   │   ├── exceptions.py       # Custom framework exception definitions
│   │   └── interpreter.py       # Core DSL execution engine
│   ├── registry/               # Parser registration & management
│   │   └── __init__.py
│   └── vault/                  # Raw log content-addressable storage
│       └── store.py            # Chain, retention tombstones, checkpoints
├── tests/                      # Framework test suites
│   ├── integration/            # Pipeline & API integration tests
│   ├── ingestion/              # Lossless capture tests
│   ├── normalization/          # OCSF validator tests
│   ├── parsers/                # Interpreter & engine unit tests
│   ├── registry/               # Registry management unit tests
│   └── vault/                  # Chain, retention, checkpoint tests
└── README.md
```

---

## ⚙️ Prerequisites & Installation

### Requirements

* **Python**: `3.10` or higher
* **Dependencies**: `jsonschema`, `pytest`, `pyyaml`

### Installation Steps

1. **Clone the repository**:

   ```bash
   git clone https://github.com/ProNeethanR/Univeral-Log-Processing.git
   cd Univeral-Log-Processing
   ```

2. **Set up Python Environment & Install Dependencies**:

   ```bash
   python -m pip install jsonschema pytest pyyaml
   ```

---

## 🧪 Running Tests & Verification

The framework includes comprehensive unit and integration test suites covering the DSL interpreter, parser registry, OCSF 1.3.0 validator, lossless raw capture, integrity chain/retention/checkpoints, quarantine records, and contract alignment.

### 1. Execute the Full Test Suite

```bash
PYTHONPATH=. python -m pytest -q
```

*Expected Output*: all tests passing (186 tests as of the Corrective Stabilization pass).

### 2. Run Test Subsets

```bash
python -m pytest tests/normalization tests/parsers tests/registry   # unit tests
python -m pytest tests/vault                                        # chain, retention, checkpoints
python -m pytest tests/ingestion                                    # lossless capture
python -m pytest tests/integration                                  # pipeline, API, contracts
```

### 3. Verify Frozen OCSF 1.3.0 Schema Checksum

Independently verify that the local OCSF schema artifact has not been modified or corrupted:

```bash
python -c "import hashlib; print(hashlib.sha256(open('schema/ocsf/ocsf_schema.json','rb').read()).hexdigest())"
```

*Expected Checksum*:
`6ccff0f70b6216abc8f82be3756a9a167662a535c64a6a60df111b0db363e3e2`

---

## 💻 Usage & Execution Examples

### 1. Validating an OCSF Event (Offline Runtime Validator)

The `OCSFValidator` component verifies candidate OCSF event dictionaries completely offline. ^lnd5me

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
    print(f" Event is valid against OCSF {result.ocsf_version} ({result.class_name})")
else:
    print(f" Validation failed with {len(result.errors)} errors:")
    for err in result.errors:
        print(f"   [{err.error_type}] Path: {err.path} -> {err.message}")

# Method B: Raising Exception on Validation Failure
try:
    validate_ocsf_event(ocsf_event, raise_on_error=True)
    print(" Event validated successfully!")
except OCSFValidationError as e:
    print(f"Error: {e}")
```

### 2. Parsing Raw Logs with the DSL Engine

Parser definitions are YAML DSL documents that conform to
`contracts/parser_mapping.schema.json` (exactly nine operations).
`ParserEngine` resolves a definition authoritatively through the parser
registry by `(source, version)`, validates it against that contract, and
executes it with `DSLInterpreter`. See `parsers/syslog.yaml` for a
shipped definition.

```python
from src.registry import register_parser, _clear_registry
from src.parsers.engine import ParserEngine

# Register the shipped syslog parser definition under (source, version)
_clear_registry()
register_parser("syslog-001", "1.0.0", "parsers/syslog.yaml")

# Resolve, contract-validate, and execute
engine = ParserEngine("syslog-001", "1.0.0")
raw_log = "Feb  1 00:00:02 bridge kernel: INBOUND TCP: IN=br0 SRC=192.150.249.87 DST=11.11.11.84 PROTO=TCP"
extracted_fields = engine.parse(raw_log)

print(extracted_fields["syslog_month"], extracted_fields["syslog_host"])
```

For direct interpreter access without registry resolution, `DSLInterpreter`
evaluates individual field definitions against a state dict:

```python
from src.parsers.interpreter import DSLInterpreter

interpreter = DSLInterpreter()
state = {"raw_event": "SRC=192.150.249.87 DST=11.11.11.84"}
print(interpreter.evaluate({"op": "extract_regex", "source": "raw_event",
                            "pattern": r"SRC=(?P<val>\S+)"}, state))
```

---

## 🔒 Security & Schema Freeze Policy

1. **OCSF Version Freeze**: The framework is pinned to **OCSF 1.3.0**. Version upgrades require explicit architectural review and update to `schema/OCSF_VERSION.md`.
2. **Air-Gapped Guarantee**: The runtime validator does not make network socket calls, DNS resolutions, or HTTP requests. It operates exclusively from local disk artifacts.
3. **Schema Integrity Safeguard**: If `schema/ocsf/ocsf_schema.json` is modified or tampered with, `OCSFValidator` will fail initialization instantly to prevent downstream invalid mappings.

---

## 📄 License & Provenance

* **Framework License**: Private / Confidential (ULPF Project).
* **Test Fixture Provenance**: Refer to [`fixtures/STATUS.md`](file:///d:/sih26/Univeral-Log-Processing/fixtures/STATUS.md) for details on sample logs obtained from Honeynet Project, AlienVault Demo scripts, and Grafana Loki repositories.
