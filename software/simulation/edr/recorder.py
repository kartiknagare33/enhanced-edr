"""
The EDR runtime — orchestrates the whole capture pipeline as a state machine.

States:
    BOOT       -> initialise everything
    MONITORING -> 100 Hz buffering + 1 Hz SD logging + crash detection
    CAPTURING  -> crash triggered; buffer frozen; collecting post-crash window
    FINALIZING -> run analytics, write flash image, assert lock, emit report
    LOCKED     -> event stored and write-protected

This is the top-level object main.py / the CLI drives. It is completely
hardware-agnostic: it takes any DataSource and never looks inside it.
"""

import os
import json
from enum import Enum

from . import config
from .core.ring_buffer import RingBuffer
from .core.detector import CrashDetector
from .core.analytics import analyze
from .storage.sd_logger import SDLogger
from .storage import flash as flashmod
from .storage.lock import MemoryLock
from .report import build_report


class State(Enum):
    BOOT = "BOOT"
    MONITORING = "MONITORING"
    CAPTURING = "CAPTURING"
    FINALIZING = "FINALIZING"
    LOCKED = "LOCKED"


class EDRRecorder:
    def __init__(self, source, workdir, scenario_name="n/a", verbose=True):
        self.source = source
        self.workdir = workdir
        self.scenario_name = scenario_name
        self.verbose = verbose

        self.state = State.BOOT
        self.buffer = RingBuffer()
        self.detector = CrashDetector()

        os.makedirs(workdir, exist_ok=True)
        self.events_dir = os.path.join(workdir, config.EVENTS_DIR)
        os.makedirs(self.events_dir, exist_ok=True)

        self.sd = SDLogger(os.path.join(workdir, config.SD_LOG_FILE))
        self.event_count = 0
        self.last_report = None
        self._trigger_info = None
        self._sd_decimator = 0

    def _log(self, msg):
        if self.verbose:
            print(msg)

    def run(self):
        """Consume the source to completion, capturing any crash events."""
        self.source.start()
        self.state = State.MONITORING
        self._log(f"[BOOT] EDR online — monitoring at {config.SAMPLE_RATE_HZ} Hz, "
                  f"{config.BUFFER_WINDOW_S}s buffer ({config.BUFFER_SIZE} samples)")

        while self.source.has_next():
            sample = self.source.read()
            self.buffer.push(sample)

            # 1 Hz continuous SD logging (decimate the 100 Hz stream).
            self._sd_decimator += 1
            if self._sd_decimator >= config.SAMPLE_RATE_HZ // config.SD_LOG_RATE_HZ:
                self.sd.log(sample)
                self._sd_decimator = 0

            if self.state == State.MONITORING:
                result = self.detector.update(sample)
                if result.triggered:
                    self._on_trigger(result, sample)

            elif self.state == State.CAPTURING:
                if self.buffer.post_count() >= config.POST_CRASH_SAMPLES:
                    self._finalize(sample)

        # Scenario ended mid-capture: finalize with what we have.
        if self.state == State.CAPTURING:
            self._finalize(self.buffer.latest() or sample)

        self.sd.close()
        self._log(f"[DONE] SD log rows: {self.sd.rows} | events captured: {self.event_count}")
        return self.last_report

    def _on_trigger(self, result, sample):
        self.state = State.CAPTURING
        self.buffer.freeze()
        self._trigger_info = result
        self._log(f"\n[CRASH] Trigger at t={sample.timestamp_ms} ms — "
                  f"{', '.join(result.reasons)}")
        self._log(f"        Buffer frozen: {len(self.buffer.pre_window())} pre-crash samples. "
                  f"Recording {config.POST_CRASH_WINDOW_S}s post-crash...")

    def _finalize(self, sample):
        self.state = State.FINALIZING
        self.event_count += 1
        event_id = f"EVENT_{self.event_count:04d}"
        event_path = os.path.join(self.events_dir, event_id)
        os.makedirs(event_path, exist_ok=True)

        window = self.buffer.window()
        analytics = analyze(window)

        # Pre-crash summary (last 5 s before impact).
        pre = self.buffer.pre_window()
        tail = pre[-config.SAMPLE_RATE_HZ * 5:] if pre else []
        pre_summary = {
            "entry_speed": round(tail[0].speed_kmph, 1) if tail else 0,
            "min_speed": round(min((s.speed_kmph for s in tail), default=0), 1),
            "max_brake": round(max((s.brake_pedal_pct for s in tail), default=0), 1),
            "max_steer": round(max((abs(s.steering_angle_deg) for s in tail), default=0), 1),
            "abs": any(s.abs_active for s in tail),
        }

        impact = window[0]
        for s in window:
            import math
            if math.hypot(s.accel_x_g, s.accel_y_g) == analytics["peak_g"]:
                impact = s
                break

        event_meta = {
            "event_id": event_id,
            "scenario": self.scenario_name,
            "triggers": self._trigger_info.reasons,
            "rtc_epoch": impact.rtc_epoch,
            "latitude": impact.latitude,
            "longitude": impact.longitude,
        }

        # --- write forensic flash image with integrity checksum ---
        lock = MemoryLock(os.path.join(event_path, config.LOCK_FILE))
        lock.guard_write()   # refuses if somehow already locked
        flash_path = os.path.join(event_path, config.FLASH_IMAGE)
        checksum = flashmod.write_crash_image(flash_path, event_meta, window, analytics)
        verified, _ = flashmod.verify_crash_image(flash_path)

        # --- full raw window (all 40 params) to the event's SD backup ---
        raw = SDLogger(os.path.join(event_path, "raw_window.csv"))
        for s in window:
            raw.log(s)
        raw.close()

        # --- assert the hardware write-protect lock ---
        lock.assert_lock(event_id, checksum)
        self.state = State.LOCKED

        integrity = {
            "sha256": checksum,
            "verified": verified,
            "locked": lock.is_locked(),
            "param_count": len(config.CRASH_CRITICAL_PARAMS),
            "sample_count": len(window),
        }

        report = build_report(event_meta, analytics, integrity, pre_summary)
        with open(os.path.join(event_path, "report.txt"), "w") as f:
            f.write(report)
        with open(os.path.join(event_path, "analytics.json"), "w") as f:
            json.dump({"event": event_meta, "analytics": analytics,
                       "integrity": integrity}, f, indent=2)

        self.last_report = report
        self._log(f"[STORED] {event_id}: analytics done, flash written, "
                  f"checksum {'PASS' if verified else 'FAIL'}, lock ENGAGED")
        self._log(f"         -> {event_path}")

        # Resume monitoring for further events.
        self.state = State.MONITORING
