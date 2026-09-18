class UnsupportedOperationError(Exception):
    """Raised when a DSL operation is not in the allowed whitelist."""
    pass

class ParserDefinitionError(Exception):
    """Raised for malformed or invalid parser definitions."""
    pass

class OCSFValidationError(Exception):
    """Raised when OCSF event fails schema validation."""
    pass
