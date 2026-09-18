import os

class RegistryError(Exception):
    """Base class for Registry exceptions."""
    pass

class DuplicateRegistrationError(RegistryError):
    """Raised when attempting to register a parser that is already registered."""
    pass

class ParserNotFoundError(RegistryError):
    """Raised when attempting to retrieve a parser that is not registered."""
    pass

_registry = {}

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

def _clear_registry():
    """Clear the registry (internal use only, for testing)."""
    _registry.clear()
