"""
Simulated SPI flash crash store with forensic integrity.

On the Pi this is the W25Q128 flash chip. Here it is a JSON file, but the
semantics that matter for a forensic recorder are preserved:

    - only the crash-critical parameter subset is written (config.CRASH_CRITICAL_PARAMS)
    - a SHA-256 checksum is computed over the payload and stored alongside it
    - read-back verifies the checksum, so tampering or corruption is detectable

The checksum is what lets an investigator prove the record is exactly what the
device wrote.
"""

import json
import hashlib
from .. import config


def _checksum(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def write_crash_image(path: str, event_meta: dict, window, analytics: dict):
    """
    Write the crash-critical subset of every sample in the window, plus event
    metadata and analytics, with an integrity checksum.
    """
    critical = [s.subset(config.CRASH_CRITICAL_PARAMS) for s in window]
    payload = {
        "event": event_meta,
        "analytics": analytics,
        "param_count": len(config.CRASH_CRITICAL_PARAMS),
        "sample_count": len(critical),
        "samples": critical,
    }
    checksum = _checksum(payload)
    image = {"payload": payload, "sha256": checksum}
    with open(path, "w") as f:
        json.dump(image, f, indent=2)
    return checksum


def verify_crash_image(path: str):
    """Return (ok, checksum). ok is False if the file was altered."""
    with open(path) as f:
        image = json.load(f)
    recomputed = _checksum(image["payload"])
    return recomputed == image["sha256"], recomputed
