# ULPF Registry Governance Contract

## Ownership
Source Profile registration is owned by the Platform Engineering team (or the equivalent ULPF Registry owner). Parsers and Source Profiles are registered separately to decouple parser evolution from source identity evolution.

## Resolution API
Consumers must not access the registry's private storage directory directly. All access must proceed through the public API boundary.

### Proposed Public API

```python
def get_source_profile(source: str, profile_version: str) -> dict:
    """
    Retrieve the authoritative Source Profile.
    
    Raises:
        ProfileNotFoundError: If the source or version is not found.
        DuplicateRegistrationError: If multiple profiles exist for the exact same key.
        InvalidProfileError: If the profile is malformed or violates the schema.
    """
    pass

def get_parser(source: str, parser_version: str) -> str:
    """
    Retrieve the registered parser definition path.
    """
    pass
```

## Determinism & Replay
The same `(source, profile_version)` combination MUST resolve deterministically.

For replay capabilities:
A replay execution MUST resolve the exact same Source Profile used originally. The `profile_version` must be explicitly provided in the replay configuration/event context. 

## Failure Semantics
All failures are fail-closed:
- **Unknown source**: explicit error (ProfileNotFoundError).
- **Unknown version**: explicit error (ProfileNotFoundError).
- **Missing profile file**: explicit error.
- **Duplicate registration**: explicit error.
- **Malformed profile**: explicit error.
