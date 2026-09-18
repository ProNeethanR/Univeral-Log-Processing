registry = {}

def register_parser(source: str, version: str, path: str):
    """Register a parser definition.
    Args:
        source: parser source identifier (e.g., 'syslog-001')
        version: version string
        path: absolute path to the YAML file
    """
    key = (source, version)
    registry[key] = path

def get_parser(source: str, version: str) -> str:
    """Retrieve the registered parser definition path.
    Raises:
        KeyError if not registered.
    """
    key = (source, version)
    if key not in registry:
        raise KeyError(f"Parser not found for source={source}, version={version}")
    return registry[key]
