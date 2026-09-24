"""Shared pytest fixtures for deterministic, order-independent demo state.

Demo data is no longer loaded as a module-import side effect. Tests that need
demo events opt in via the ``demo_data`` fixture, which clears shared module
state, loads the demo fixture into an isolated vault backend, and restores the
previous state afterwards. Results therefore never depend on import or
collection order.
"""

import os

import pytest

from src.api.services import event_service, quarantine_service, run_service
from src.vault import store as vault


@pytest.fixture
def isolated_vault(tmp_path):
    prior = vault._BACKEND
    vault.configure_backend(vault.FileVaultBackend(tmp_path / "ulpf-test-vault"))
    yield
    vault.configure_backend(prior)


@pytest.fixture
def demo_data(isolated_vault):
    """Deterministically load demo events into clean module state."""
    previous_env = os.environ.get("ULPF_DEMO_DATA")
    previous_events = list(event_service._events)
    previous_summaries = list(event_service._summaries)
    previous_failures = list(quarantine_service._failures)
    previous_runs = dict(run_service._runs)
    previous_run_event_ids = {k: list(v) for k, v in run_service._run_event_ids.items()}
    previous_active_parsers = event_service._active_parsers

    os.environ["ULPF_DEMO_DATA"] = "true"
    event_service.load_demo_data()
    run_service.ensure_demo_run()

    try:
        assert event_service._events, "Demo data failed to load"
        yield event_service._events
    finally:
        os.environ.pop("ULPF_DEMO_DATA", None)
        if previous_env is not None:
            os.environ["ULPF_DEMO_DATA"] = previous_env
        event_service._events[:] = previous_events
        event_service._summaries[:] = previous_summaries
        event_service._active_parsers = previous_active_parsers
        quarantine_service._failures[:] = previous_failures
        run_service._runs.clear()
        run_service._runs.update(previous_runs)
        run_service._run_event_ids.clear()
        run_service._run_event_ids.update(previous_run_event_ids)