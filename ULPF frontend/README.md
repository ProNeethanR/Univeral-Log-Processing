# ULPF Web Dashboard

This directory contains the standalone/static dashboard artifact used for the ULPF project presentation and web deployment.

## Contents

- `code.html` — standalone dashboard HTML artifact.
- `screen.png` — dashboard screenshot used in the main repository README.
- `DESIGN.md` — visual design specification.

## Important distinction

The repository also contains an integrated dashboard under:

```text
src/api/static/
```

That dashboard is served directly by the FastAPI backend.

The HTML in this directory is a separate static frontend artifact. Its presentation content should not be treated as proof of live backend telemetry; runtime API responses from the FastAPI service are authoritative.

## Render deployment

For a standalone Render Static Site, use:

```text
Root Directory: ULPF frontend
```

The static host needs an `index.html` entry point. The current artifact is named `code.html`; either configure the host to serve that file as the entry page or rename/copy it to `index.html` as part of the deployment workflow.

If the standalone frontend is changed to call the backend API, configure its API base URL to the deployed FastAPI service and enable the appropriate CORS policy on the backend.

## Dashboard screenshot

The screenshot in `screen.png` is a visual reference for the dashboard layout. Values shown in the image may be presentation/demo data and should not be interpreted as live measurements.
