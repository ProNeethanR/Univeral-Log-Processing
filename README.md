# Universal Log Processing Framework (ULPF)

**Universal Log Processing Framework (ULPF)** is a deterministic, high-assurance log processing and normalization architecture. It ingests raw, heterogeneous enterprise log streams (Syslog, CEF, vendor formats), stores them in a tamper-evident vault, extracts structured fields using a declarative DSL interpreter, and validates normalized events against the frozen **OCSF (Open Cybersecurity Schema Framework) 1.3.0** standard completely offline.

---

## 🚀 Key Features

* **Deterministic DSL-Driven Parsing Engine**: Executes declarative YAML parser rules to parse, tokenize, and transform raw unformatted logs into structured JSON without arbitrary code execution.
* **Air-Gapped OCSF 1.3.0 Runtime Validator**: Validates candidate normalized events strictly against a local, frozen OCSF 1.3.0 schema artifact (`schema/ocsf/ocsf_schema.json`). Works 100% offline without remote network schema lookups.
* **Cryptographic Schema Integrity**: Automatically verifies the SHA-256 checksum (`6ccff0f70b6216abc8f82be3756a9a167662a535c64a6a60df111b0db363e3e2`) and version (`1.3.0`) of the frozen OCSF schema upon initialization.
* **Tamper-Evident Raw Log Vault**: Stores raw unparsed logs with SHA-256 payload digests and locator metadata to guarantee end-to-end data provenance.
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
│   └── event_contract.schema.json
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
│   ├── ingestion/              # Ingestor pipeline & raw ref generator
│   │   └── ingestor.py
│   ├── normalization/          # OCSF mapper & runtime validator
│   │   ├── mapper.py           # Field normalization mapper
│   │   └── ocsf_validator.py   # Air-gapped OCSF 1.3.0 validator
│   ├── parsers/                # DSL parsing engine & interpreter
│   │   ├── dsl_validator.py    # DSL syntax validator
│   │   ├── engine.py           # High-level parser engine interface
│   │   ├── exceptions.py       # Custom framework exception definitions
│   │   └── interpreter.py      # Core DSL execution engine
│   ├── registry/               # Parser registration & management
│   │   └── __init__.py
│   └── vault/                  # Raw log content-addressable storage
│       └── store.py
├── tests/                      # Framework test suites
│   ├── integration/            # Pipeline integration tests
│   ├── normalization/          # OCSF validator tests
│   ├── parsers/                # Interpreter & engine unit tests
│   └── registry/               # Registry management unit tests
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

The framework includes comprehensive unit and integration test suites covering the DSL interpreter, parser registry, and OCSF 1.3.0 validator.

### 1. Execute All Framework Unit Tests

Run `pytest` to execute all unit tests across normalization, parsers, and registry modules:

```bash
python -m pytest tests/normalization tests/parsers tests/registry
```

*Expected Output*:

```text
============================= test session starts =============================
collected 39 items

tests/normalization/test_ocsf_validator.py .........                     [ 23%]
tests/parsers/test_interpreter.py ......................                 [ 78%]
tests/registry/test_registry.py ........                                 [100%]

============================= 39 passed in 0.30s ==============================
```

### 2. Execute Integration Tests

Run the end-to-end Syslog ingestion pipeline test:

```bash
python -m pytest tests/integration/test_syslog_pipeline.py
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
    print(f"✅ Event is valid against OCSF {result.ocsf_version} ({result.class_name})")
else:
    print(f"❌ Validation failed with {len(result.errors)} errors:")
    for err in result.errors:
        print(f"   [{err.error_type}] Path: {err.path} -> {err.message}")

# Method B: Raising Exception on Validation Failure
try:
    validate_ocsf_event(ocsf_event, raise_on_error=True)
    print("✅ Event validated successfully!")
except OCSFValidationError as e:
    print(f"❌ Error: {e}")
```

### 2. Parsing Raw Logs with the DSL Engine

```python
from src.parsers.interpreter import DSLInterpreter

# Load a YAML DSL parser definition
dsl_def = {
    "parser": {
        "id": "syslog-parser",
        "version": "1.0.0"
    },
    "rules": [
        {
            "match": ".*",
            "actions": [
                {"grok": "%{SYSLOGTIMESTAMP:syslog_time} %{HOSTNAME:syslog_host} %{GREEDYDATA:message}"}
            ]
        }
    ]
}

# Instantiate interpreter and parse raw log line
interpreter = DSLInterpreter(dsl_def)
raw_log = "Sep 18 14:32:10 firewall-01 IN=eth0 OUT=eth1 SRC=192.168.1.50 DST=10.0.0.1 PROTO=TCP"
extracted_fields = interpreter.parse(raw_log)

print("Extracted Fields:", extracted_fields)
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
