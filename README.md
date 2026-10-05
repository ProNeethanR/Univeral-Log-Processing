# ULPF — Universal Log Processing Framework

ULPF is a loss-aware log processing framework for ingesting heterogeneous security logs, preserving raw evidence, parsing with declarative rules, normalizing events to **OCSF 1.3.0**, validating the result, and exposing the pipeline through a FastAPI API and web dashboard.

The design emphasizes **raw-byte preservation, provenance, deterministic parsing, schema validation, integrity verification, and explicit failure/quarantine handling**.

## Dashboard

The repository includes an integrated dashboard served by the FastAPI application and a separate frontend artifact under `ULPF frontend/`.

![ULPF web dashboard](<ULPF frontend/screen.png>)

The dashboard is organized around operational views for:

- Overview and pipeline health
- Events and event inspection
- Vault and integrity verification
- Quarantine / dead-letter records
- Source profiles
- Parser plugins
- Benchmarking
- Ingest testing
- Pipeline studio
- Verification runs

> The screenshot is a UI reference image committed in `ULPF frontend/screen.png`. Some dashboard numbers and connector labels shown in the visual are demonstration data; runtime API responses are authoritative.

## Core pipeline

```text
Raw logs
   |
   v
Ingestion
   |
   +----> Raw Vault / SHA-256 / offsets / references
   |
   v
Format detection + parser registry
   |
   v
YAML DSL parser
   |
   v
OCSF 1.3.0 normalization
   |
   v
Local OCSF schema validation
   |
   +--------------------+
   |                    |
   v                    v
Validated event      Quarantine / failure record
   |
   v
FastAPI API + dashboard
```

## What is implemented

### Lossless evidence handling
Raw input can be stored as byte-addressed evidence with SHA-256 references and record metadata. Record splitting is a separate concern from whole-file ingestion, so do not assume `ingest_file()` performs logical event grouping.

### Declarative parsing
Parser definitions live in `parsers/` and are interpreted through the parser/DSL components under `src/parsers/`.

### OCSF 1.3.0 validation
ULPF keeps a local OCSF schema under `schema/ocsf/` and validates normalized events without needing to fetch a schema at runtime.

### Provenance and trust
Event envelopes carry source identity, raw references, integrity state, parser metadata, provenance, evidence classification, and a trust gate.

### Quarantine
Parsing, normalization, validation, and integrity failures are represented as structured failure records without embedding raw log content in the failure record itself.

### Persistence
Pipeline state can be persisted through the SQLite layer under `src/storage/`. For hosted deployments, persistent storage must be configured separately because local filesystem state should not be assumed to survive every platform restart/redeploy.

## Repository layout

```text
.
├── contracts/                  # JSON Schema contracts
├── data/                      # Local pipeline state (development/runtime)
├── docs/                      # Architecture, decisions, hardening, stabilization
├── fixtures/
│   ├── raw/                   # Raw sample logs
│   ├── ground_truth/          # Expected normalized outputs
│   └── provenance/            # Fixture provenance and licensing notes
├── parsers/                   # Declarative parser definitions
├── schema/                    # Frozen local OCSF schema
├── src/
│   ├── api/                   # FastAPI application, models, services, dashboard
│   ├── ingestion/             # Raw ingestion and record splitting
│   ├── normalization/         # OCSF mapping and validation
│   ├── parsers/               # Parser engine and DSL interpreter
│   ├── registry/              # Source/parser registry
│   ├── storage/               # SQLite persistence
│   └── vault/                 # Raw vault and integrity chain
├── tests/                     # Automated test suite
├── ULPF frontend/             # Separate static frontend/reference artifact
├── demo.py                    # CLI demonstration
└── requirements.txt           # Python dependencies
```

## Quick start

### Requirements

- Python 3.10+
- A modern browser
- No Node.js is required for the integrated FastAPI-served dashboard

### Install

```bash
git clone https://github.com/ProNeethanR/Univeral-Log-Processing.git
cd Univeral-Log-Processing

python -m venv venv

# Windows PowerShell
.\\venv\\Scripts\\Activate.ps1

# Linux / macOS
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### Run the integrated backend + dashboard

```bash
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Open:

| URL | Purpose |
|---|---|
| `http://127.0.0.1:8000/` | Web dashboard |
| `http://127.0.0.1:8000/docs` | FastAPI / Swagger documentation |

The FastAPI application is defined in `src/api/main.py`.

### CLI demo

```bash
python demo.py
```

## API

### Dashboard and events

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/summary` | Pipeline summary and latest run |
| GET | `/api/events` | Paginated event list with filters |
| GET | `/api/events/{event_id}` | Event detail |
| GET | `/api/events/{event_id}/raw` | Raw log representation |
| GET | `/api/events/{event_id}/parsed` | Parsed fields |
| GET | `/api/events/{event_id}/normalized` | OCSF-normalized event |
| GET | `/api/events/{event_id}/validation` | Validation result |
| GET | `/api/events/{event_id}/envelope` | Full ULPF event envelope |

### Integrity and quarantine

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/integrity/verify` | Verify the vault chain/checkpoint state |
| POST | `/api/integrity/checkpoint` | Create an integrity checkpoint |
| GET | `/api/quarantine` | Query failure/quarantine records |
| POST | `/api/quarantine/reprocess` | Reprocess quarantined failures |

### Runs and interactive operations

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/runs` | Pipeline run history |
| GET | `/api/runs/{run_id}` | Single run |
| GET | `/api/runs/{run_id}/events` | Events belonging to a run |
| POST | `/api/demo/run` | Run the demo pipeline |
| POST | `/api/test-parse` | Test parsing for a supplied raw log |
| GET | `/api/sources` | Source/connector view |
| GET | `/api/plugins` | Parser/plugin view |
| GET | `/api/persistence/status` | Persistence status |
| POST | `/api/pipeline/reset` | Reset pipeline state |

## Frontend deployment

The repository contains two dashboard-related frontend forms:

1. **Integrated dashboard** — served directly by FastAPI from `src/api/static/`.
2. **Separate static frontend artifact** — stored under `ULPF frontend/`.

For a Render deployment of the backend:

```text
Service type: Web Service
Root directory: repository root
Build command: pip install -r requirements.txt
Start command: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
```

For the separate `ULPF frontend/` artifact, use that directory as the Render root only after ensuring the artifact has an `index.html` entry point and that its JavaScript is configured to call the deployed API.

## Testing

Run the complete suite with:

```bash
python -m pytest -q -p no:cacheprovider
```

The latest stabilized repository baseline recorded **186 tests passing**.

For stronger CI validation:

```bash
python -m pytest -q -p no:cacheprovider -W error::DeprecationWarning
```

## Important semantics

### Whole-file ingestion vs record splitting

`ingest_file()` currently represents the supplied file as one stored record with offsets covering the entire file.

`split_raw_records()` is the separate record-boundary operation.

`ingest_batch()` accepts already separated inputs and assigns record indexes.

Do not document `ingest_file()` as a multiline/logical-record parser.

### Multiline logs

The repository contains tests for byte preservation across multiline-looking input. Whether multiple physical lines are grouped into one logical event is a parser/record-boundary concern and must be verified against the current implementation before claiming full multiline grouping support.

## Fixture provenance

See [`fixtures/provenance/README.md`](fixtures/provenance/README.md) for source classification, hashes, byte lengths, and licensing notes for the frozen fixture corpus.

Do not treat documentation-derived or reference examples as real-world captures unless the provenance file explicitly classifies them as real.

## Schema integrity

The OCSF schema is stored locally under `schema/ocsf/`. The validator checks the pinned schema material rather than downloading a replacement at runtime.

## Development principles

- Preserve raw evidence before parsing or normalization.
- Prefer deterministic behavior over implicit inference.
- Keep source context authoritative and fail closed when required provenance is unavailable.
- Make parser behavior explicit and testable.
- Never hide failures by weakening or skipping tests.
- Distinguish verified implementation from UI/demo presentation data.
- Avoid introducing new dependencies or architecture without a project-level reason.

## Project status

The current repository includes the corrective stabilization work and a green automated test baseline. Continued development should focus on gaps that are demonstrable from the real production paths rather than treating the test count alone as proof that every planned phase is complete.

## License / fixture use

ULPF is a project repository rather than a released public software package. Some fixtures have source-specific licensing or redistribution constraints; consult `fixtures/provenance/README.md` before redistributing fixture data.
