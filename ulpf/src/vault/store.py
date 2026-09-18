"""
vault/store.py
--------------
In-memory content-addressed vault.

Stores raw bytes keyed by SHA-256 digest.
Returns a locator string (sha256:<hex>) and the digest itself.

Security contract:
  - Only stores bytes; never interprets content.
  - SHA-256 is computed over the exact bytes supplied.
  - No external I/O beyond optional dump_to_path.
"""

import hashlib
import os
from typing import Optional


_STORE: dict[str, bytes] = {}


def put(raw_bytes: bytes) -> tuple[str, str]:
    """
    Store raw bytes in the vault.

    Returns
    -------
    (locator, sha256_hex)
        locator  : str  — "sha256:<hex>" — the canonical reference
        sha256_hex : str — lowercase hex digest
    """
    digest = hashlib.sha256(raw_bytes).hexdigest()
    locator = f"sha256:{digest}"
    _STORE[digest] = raw_bytes
    return locator, digest


def get(locator: str) -> bytes:
    """
    Retrieve raw bytes by locator.

    Parameters
    ----------
    locator : str
        Must be in the form "sha256:<hex>".

    Raises
    ------
    KeyError
        If the locator is not found.
    ValueError
        If the locator format is invalid.
    """
    if not locator.startswith("sha256:"):
        raise ValueError(f"Invalid locator format: {locator!r}")
    digest = locator[len("sha256:"):]
    if digest not in _STORE:
        raise KeyError(f"Locator not found in vault: {locator!r}")
    return _STORE[digest]


def verify(locator: str) -> bool:
    """
    Re-compute SHA-256 of stored bytes and confirm it matches the locator.

    Returns True if the stored bytes are intact, False if corrupted.
    """
    if not locator.startswith("sha256:"):
        raise ValueError(f"Invalid locator format: {locator!r}")
    digest = locator[len("sha256:"):]
    raw = _STORE.get(digest)
    if raw is None:
        return False
    recomputed = hashlib.sha256(raw).hexdigest()
    return recomputed == digest


def dump_to_path(locator: str, path: str) -> None:
    """
    Write vault contents to a file path. Used only for debugging / test output.
    Does not affect the in-memory store.
    """
    raw = get(locator)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(raw)


def clear() -> None:
    """Clear the in-memory vault. Used in tests only."""
    _STORE.clear()
