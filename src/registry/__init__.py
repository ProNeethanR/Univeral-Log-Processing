import os
import json
from enum import Enum
from pathlib import Path
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

DEFAULT_SOURCE_CONTEXT_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "contracts" / "source_context.schema.json"

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
    """Register a source profile definition and validate against schema.
    Args:
        source: source identifier
        profile_version: profile version string
        profile_data: the loaded JSON profile dict
    """
    key = _profile_key(source, profile_version)
    if key in _profile_registry:
        raise DuplicateRegistrationError(f"Source profile already registered for source={source}, profile_version={profile_version}")

    with open(DEFAULT_SOURCE_CONTEXT_SCHEMA_PATH, 'r') as f:
        schema = json.load(f)

    try:
        jsonschema.validate(instance=profile_data, schema=schema)
    except jsonschema.ValidationError as e:
        raise InvalidProfileError(f"Source profile validation failed: {e.message}") from e

    if profile_data.get("source") != source or profile_data.get("profile_version") != profile_version:
        raise InvalidProfileError("Source profile identity does not match its registry key")

    state = ProfileState.ACTIVE if activate else ProfileState.REGISTERED
    _profile_registry[key] = {"profile": dict(profile_data), "state": state}

def get_source_profile(source: str, profile_version: str) -> dict:
    """Retrieve the registered source profile definition.
    Raises:
        ProfileNotFoundError if not registered.
    """
    key = _profile_key(source, profile_version)
    if key not in _profile_registry:
        raise ProfileNotFoundError(f"Source profile not found for source={source}, profile_version={profile_version}")

    record = _profile_registry[key]
    if record["state"] != ProfileState.ACTIVE:
        raise ProfileInactiveError(f"Source profile is not active for source={source}, profile_version={profile_version}")

    return dict(record["profile"])

def get_source_profile_state(source: str, profile_version: str) -> ProfileState:
    """Return the lifecycle state for one exact registered profile."""
    key = _profile_key(source, profile_version)
    if key not in _profile_registry:
        raise ProfileNotFoundError(f"Source profile not found for source={source}, profile_version={profile_version}")
    return _profile_registry[key]["state"]

def activate_source_profile(source: str, profile_version: str) -> None:
    """Activate one exact, already validated source profile."""
    key = _profile_key(source, profile_version)
    if key not in _profile_registry:
        raise ProfileNotFoundError(f"Source profile not found for source={source}, profile_version={profile_version}")
    _profile_registry[key]["state"] = ProfileState.ACTIVE

def deactivate_source_profile(source: str, profile_version: str) -> None:
    """Deactivate one exact source profile without deleting its registration."""
    key = _profile_key(source, profile_version)
    if key not in _profile_registry:
        raise ProfileNotFoundError(f"Source profile not found for source={source}, profile_version={profile_version}")
    _profile_registry[key]["state"] = ProfileState.INACTIVE

def list_source_profiles() -> list[tuple[str, str, ProfileState]]:
    """List registered profiles in deterministic source/version order."""
    return [
        (source, version, _profile_registry[(source, version)]["state"])
        for source, version in sorted(_profile_registry)
    ]

def _clear_registry():
    """Clear the registries (internal use only, for testing)."""
    _registry.clear()
    _profile_registry.clear()
