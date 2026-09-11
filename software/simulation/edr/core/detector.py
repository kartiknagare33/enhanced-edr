"""
Crash detector.

Evaluates each incoming sample against four independent trigger conditions, any
one of which declares a crash:

    1. IMU G-spike   : net horizontal acceleration (gravity removed) exceeds a
                       threshold.
    2. Speed delta   : an abrupt speed loss between consecutive samples that is
                       only possible in a collision.
    3. ECU crash flag: the vehicle ECU itself asserted a crash over CAN.
    4. Power fail    : supply voltage collapsed (impact severed power).

The redundancy is deliberate: a real crash rarely presents through only one
channel, and any single sensor may fail. A short debounce prevents one event
from triggering repeatedly.
"""

import math
from .. import config


class TriggerResult:
    def __init__(self, triggered, reasons=None, net_g=0.0, speed_delta=0.0):
        self.triggered = triggered
        self.reasons = reasons or []
        self.net_g = net_g
        self.speed_delta = speed_delta

    def __bool__(self):
        return self.triggered


class CrashDetector:
    def __init__(self):
        self._prev_speed = None
        self._debounce = 0

    def update(self, sample) -> TriggerResult:
        reasons = []

        # Net horizontal acceleration with gravity removed.
        net_g = math.hypot(sample.accel_x_g, sample.accel_y_g)

        # Speed change since last sample (km/h per tick).
        speed_delta = 0.0
        if self._prev_speed is not None:
            speed_delta = self._prev_speed - sample.speed_kmph
        self._prev_speed = sample.speed_kmph

        # Debounce window after a trigger.
        if self._debounce > 0:
            self._debounce -= 1
            return TriggerResult(False, net_g=net_g, speed_delta=speed_delta)

        if net_g >= config.CRASH_ACCEL_THRESHOLD_G:
            reasons.append(f"IMU G-spike ({net_g:.1f} g)")
        if speed_delta >= config.CRASH_SPEED_DELTA_KMPH:
            reasons.append(f"Speed drop ({speed_delta:.1f} km/h/tick)")
        if sample.crash_flag_ecu:
            reasons.append("ECU crash flag")
        if sample.power_fail:
            reasons.append("Power fail")

        if reasons:
            self._debounce = config.TRIGGER_DEBOUNCE_SAMPLES
            return TriggerResult(True, reasons, net_g, speed_delta)

        return TriggerResult(False, net_g=net_g, speed_delta=speed_delta)
