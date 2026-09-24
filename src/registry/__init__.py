import os
import json
import tempfile
import threading
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import jsonschema

class RegistryError(Exception):
    """Base class for Registry exceptions."""
    pass

class DuplicateRegistrationError(RegistryError):
    """Raised when attempting to register a parser or profile that is already registered."""
    pass

class ParserNotFoundError(RegistryError):
    """Raised when attempting to retrieve a parser that is not registered."""
    pass

class ProfileNotFoundError(RegistryError):
    """Raised when attempting to retrieve a source profile that is not registered."""
    pass

class InvalidProfileError(RegistryError):
    """Raised when a source profile fails schema validation."""
    pass

class ProfileInactiveError(RegistryError):
    """Raised when a source profile exists but is not active."""
    pass

class AmbiguousProfileError(RegistryError):
    """Raised when a source profile lookup does not identify one exact version."""
    pass

class ProfileState(str, Enum):
    REGISTERED = "registered"
    ACTIVE = "active"
    INACTIVE = "inactive"

_registry = {}
_profile_registry = {}
_storage_lock = threading.Lock()

DEFAULT_SOURCE_CONTEXT_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "contracts" / "source_context.schema.json"
_storage_dir: Optional[Path] = None


def _get_storage_dir() -> Path:
    global _storage_dir
    if _storage_dir is None:
        env_path = os.environ.get("ULPF_REGISTRY_PATH")
        if env_path:
            _storage_dir = Path(env_path)
        else:
            _storage_dir = Path(tempfile.gettempdir()) / "ulpf_registry" / "profiles"
    _storage_dir.mkdir(parents=True, exist_ok=True)
    return _storage_dir


def configure_profile_storage(storage_path: Optional[Union[str, Path]]) -> None:
    """Configure or reset the durable filesystem storage directory for source profiles."""
    global _storage_dir
    with _storage_lock:
        if storage_path is None:
            env_path = os.environ.get("ULPF_REGISTRY_PATH")
            if env_path:
                _storage_dir = Path(env_path)
            else:
                _storage_dir = Path(tempfile.gettempdir()) / "ulpf_registry" / "profiles"
        else:
            _storage_dir = Path(storage_path)
        _storage_dir.mkdir(parents=True, exist_ok=True)
        _load_persisted_profiles()


def _profile_file_path(source: str, profile_version: str) -> Path:
    filename = f"{source}__{profile_version}.json"
    return _get_storage_dir() / filename


def _load_persisted_profiles() -> None:
    """Load and validate all persisted profiles from the storage directory.

    Corrupt or schema-invalid profiles fail explicitly with InvalidProfileError.
    """
    _profile_registry.clear()
    storage = _get_storage_dir()
    if not storage.exists():
        return

    with open(DEFAULT_SOURCE_CONTEXT_SCHEMA_PATH, 'r', encoding="utf-8") as f:
        schema = json.load(f)

    for item in sorted(storage.glob("*.json")):
        try:
            content = json.loads(item.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InvalidProfileError(f"Corrupt profile storage file {item.name}: {exc}") from exc

        if not isinstance(content, dict):
            raise InvalidProfileError(f"Invalid profile storage structure in {item.name}: expected dict")

        source = content.get("source")
        profile_version = content.get("profile_version")
        raw_state = content.get("state")
        profile_data = content.get("profile")

        if not source or not profile_version or not raw_state or not isinstance(profile_data, dict):
            raise InvalidProfileError(f"Persisted profile {item.name} is missing required envelope fields")

        try:
            state = ProfileState(raw_state)
        except ValueError as exc:
            raise InvalidProfileError(f"Persisted profile {item.name} has invalid state: {raw_state!r}") from exc

        try:
            jsonschema.validate(instance=profile_data, schema=schema)
        except jsonschema.ValidationError as exc:
            raise InvalidProfileError(f"Persisted profile {item.name} failed schema validation: {exc.message}") from exc

        if profile_data.get("source") != source or profile_data.get("profile_version") != profile_version:
            raise InvalidProfileError(f"Persisted profile {item.name} identity does not match envelope")

        key = _profile_key(source, profile_version)
        if key in _profile_registry:
            raise DuplicateRegistrationError(f"Duplicate profile detected in storage: {key}")

        _profile_registry[key] = {"profile": dict(profile_data), "state": state}


# Initialize on import
_load_persisted_profiles()


def register_parser(source: str, version: str, path: str):
    """Register a parser definition.
    Args:
        source: parser source identifier (e.g., 'syslog-001')
        version: version string
        path: absolute path to the YAML file
    """
    key = (source, version)
    if key in _registry:
        raise DuplicateRegistrationError(f"Parser already registered for source={source}, version={version}")
    _registry[key] = path


def get_parser(source: str, version: str) -> str:
    """Retrieve the registered parser definition path.
    Raises:
        ParserNotFoundError if not registered.
    """
    key = (source, version)
    if key not in _registry:
        raise ParserNotFoundError(f"Parser not found for source={source}, version={version}")

    path = _registry[key]
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Registered parser path does not exist: {path}")

    return path


def _profile_key(source: str, profile_version: str) -> tuple[str, str]:
    if not isinstance(source, str) or not source.strip():
        raise AmbiguousProfileError("Source profile lookup requires a non-empty source")
    if not isinstance(profile_version, str) or not profile_version.strip():
        raise AmbiguousProfileError("Source profile lookup requires an exact profile version")
    return source, profile_version


def register_source_profile(
    source: str,
    profile_version: str,
    profile_data: dict,
    *,
    activate: bool = True,
):
    """Register a source profile definition, persist it durably, and validate against schema.
    Args:
        source: source identifier
        profile_version: profile version string
        profile_data: the loaded JSON profile dict
        activate: whether to immediately activate the profile for new ingestion
    """
    key = _profile_key(source, profile_version)
    with _storage_lock:
        file_path = _profile_file_path(source, profile_version)
        if key in _profile_registry or file_path.exists():
            raise DuplicateRegistrationError(
                f"Source profile already registered for source={source}, profile_version={profile_version}"
            )

        with open(DEFAULT_SOURCE_CONTEXT_SCHEMA_PATH, 'r', encoding="utf-8") as f:
            schema = json.load(f)

        try:
            jsonschema.validate(instance=profile_data, schema=schema)
        except jsonschema.ValidationError as e:
            raise InvalidProfileError(f"Source profile validation failed: {e.message}") from e

        if profile_data.get("source") != source or profile_data.get("profile_version") != profile_version:
            raise InvalidProfileError("Source profile identity does not match its registry key")

        state = ProfileState.ACTIVE if activate else ProfileState.REGISTERED

        envelope = {
            "source": source,
            "profile_version": profile_version,
            "state": state.value,
            "profile": dict(profile_data),
        }
        file_path.write_text(json.dumps(envelope, indent=2, sort_keys=True), encoding="utf-8")

        _profile_registry[key] = {"profile": dict(profile_data), "state": state}


def get_source_profile(source: str, profile_version: str) -> dict:
    """Retrieve the registered source profile definition for new ingestion.

    Only profiles in the ACTIVE state are accessible through this API.

    Raises:
        ProfileNotFoundError if not registered.
        ProfileInactiveError if registered but not active.
    """
    key = _profile_key(source, profile_version)
    if key not in _profile_registry:
        raise ProfileNotFoundError(f"Source profile not found for source={source}, profile_version={profile_version}")

    record = _profile_registry[key]
    if record["state"] != ProfileState.ACTIVE:
        raise ProfileInactiveError(f"Source profile is not active for source={source}, profile_version={profile_version}")

    return dict(record["profile"])


def get_historical_source_profile(source: str, profile_version: str) -> dict:
    """Retrieve an authoritative Source Profile for historical replay.

    Permits retrieval of both ACTIVE and INACTIVE profiles without
    reactivating them for new ingestion. Unactivated profiles in REGISTERED
    state remain unretrievable.

    Raises:
        ProfileNotFoundError: If the profile is not registered.
        ProfileInactiveError: If the profile was never activated (REGISTERED state).
    """
    key = _profile_key(source, profile_version)
    if key not in _profile_registry:
        raise ProfileNotFoundError(f"Source profile not found for source={source}, profile_version={profile_version}")

    record = _profile_registry[key]
    if record["state"] == ProfileState.REGISTERED:
        raise ProfileInactiveError(
            f"Source profile was never activated for source={source}, profile_version={profile_version}"
        )

    return dict(record["profile"])


def resolve_replay_context(source: str, profile_version: str) -> dict:
    """Convenience alias for resolving historical Source Profile in replay pipelines."""
    return get_historical_source_profile(source, profile_version)


def get_source_profile_state(source: str, profile_version: str) -> ProfileState:
    """Return the lifecycle state for one exact registered profile."""
    key = _profile_key(source, profile_version)
    if key not in _profile_registry:
        raise ProfileNotFoundError(f"Source profile not found for source={source}, profile_version={profile_version}")
    return _profile_registry[key]["state"]


def activate_source_profile(source: str, profile_version: str) -> None:
    """Activate one exact, already validated source profile and update durable storage."""
    key = _profile_key(source, profile_version)
    with _storage_lock:
        if key not in _profile_registry:
            raise ProfileNotFoundError(f"Source profile not found for source={source}, profile_version={profile_version}")
        _profile_registry[key]["state"] = ProfileState.ACTIVE
        file_path = _profile_file_path(source, profile_version)
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                data["state"] = ProfileState.ACTIVE.value
                file_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
            except OSError:
                pass


def deactivate_source_profile(source: str, profile_version: str) -> None:
    """Deactivate one exact source profile without deleting its registration."""
    key = _profile_key(source, profile_version)
    with _storage_lock:
        if key not in _profile_registry:
            raise ProfileNotFoundError(f"Source profile not found for source={source}, profile_version={profile_version}")
        _profile_registry[key]["state"] = ProfileState.INACTIVE
        file_path = _profile_file_path(source, profile_version)
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                data["state"] = ProfileState.INACTIVE.value
                file_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
            except OSError:
                pass


def list_source_profiles() -> list[tuple[str, str, ProfileState]]:
    """List registered profiles in deterministic source/version order."""
    return [
        (source, version, _profile_registry[(source, version)]["state"])
        for source, version in sorted(_profile_registry)
    ]


def _clear_registry():
    """Clear the registries and remove persisted test profile files (for testing)."""
    with _storage_lock:
        _registry.clear()
        _profile_registry.clear()
        storage = _get_storage_dir()
        if storage.exists():
            for p in storage.glob("*.json"):
                try:
                    p.unlink()
                except OSError:
                    pass
