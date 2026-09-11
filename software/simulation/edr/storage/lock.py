"""
Forensic memory lock (simulated hardware write-protect).

On the Pi this is a GPIO pin driving the flash chip's WP (write-protect) pin:
once asserted after a crash write, the flash physically cannot be overwritten
until a power cycle. Here it is a lock file plus an in-process guard that raises
if anything tries to modify a locked event. The point is the same — proving the
crash record could not have been altered after the fact.
"""

import os
import json
import time


class MemoryLock:
    def __init__(self, path):
        self.path = path

    def is_locked(self):
        return os.path.exists(self.path)

    def assert_lock(self, event_id, checksum):
        if self.is_locked():
            raise PermissionError("Memory already locked; write-protect active.")
        with open(self.path, "w") as f:
            json.dump(
                {
                    "locked": True,
                    "event_id": event_id,
                    "sha256": checksum,
                    "locked_at": time.time(),
                },
                f,
                indent=2,
            )

    def guard_write(self):
        """Call before any write that must be blocked once locked."""
        if self.is_locked():
            raise PermissionError(
                "Write refused: memory is write-protected (forensic lock active)."
            )

    def release(self):
        """Simulates a power-cycle / authorised reset."""
        if os.path.exists(self.path):
            os.remove(self.path)
