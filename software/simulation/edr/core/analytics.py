"""
Crash analytics engine.

Given the frozen event window, this computes the metrics a real Event Data
Recorder reports:

    peak_g            : maximum net horizontal acceleration during the event.
    delta_v_kmph      : change in velocity across the crash pulse (integrated
                        from acceleration) — the single most established
                        crash-severity metric in real EDR / accident work.
    pdof_deg          : Principal Direction Of Force, in vehicle frame.
    impact_direction  : that angle mapped to a named sector (Frontal, Rear,
                        Left, Right, and oblique combinations).
    rollover          : whether roll exceeded the rollover threshold.
    csi               : Crash Severity Index 0..100 (peak_g vs a reference).
    severity          : Minor / Moderate / Severe (from delta-V bands).

Sign convention (matches model.py): a frontal impact reads negative accel_x, so
the force *came from* +x (the front). impact direction = -accel vector.
"""

import math
from .. import config

G = 9.81


def analyze(window):
    """window : list[EDRSample] covering pre- and post-crash. Returns a dict."""
    if not window:
        return {}

    # --- peak acceleration and the sample where it occurred ---
    peak_g = 0.0
    peak_sample = window[0]
    for s in window:
        net = math.hypot(s.accel_x_g, s.accel_y_g)
        if net > peak_g:
            peak_g = net
            peak_sample = s

    # --- delta-V: the speed change across the crash pulse ---
    # Delta-V is the drop in vehicle speed caused by the impact. We measure the
    # speed just before the peak against the minimum shortly after it — this is
    # the physically meaningful crash delta-V, and it is bounded by real speed.
    peak_idx = window.index(peak_sample)
    pre_window = window[max(0, peak_idx - 10):peak_idx + 1]
    post_window = window[peak_idx:peak_idx + 30]
    speed_before = max((s.speed_kmph for s in pre_window), default=peak_sample.speed_kmph)
    speed_after = min((s.speed_kmph for s in post_window), default=peak_sample.speed_kmph)
    delta_v_kmph = max(0.0, speed_before - speed_after)

    # --- principal direction of force (PDOF) ---
    # Force direction is opposite to the measured acceleration vector.
    fx = -peak_sample.accel_x_g
    fy = -peak_sample.accel_y_g
    pdof_deg = math.degrees(math.atan2(fy, fx))     # 0 = front, 90 = left
    impact_direction = _sector(pdof_deg)

    # --- rollover ---
    max_roll = max(abs(s.roll_deg) for s in window)
    rollover = max_roll >= config.ROLLOVER_ANGLE_DEG

    # --- indices / classification ---
    csi = min(100.0, (peak_g / config.CSI_REFERENCE_G) * 100.0)
    severity = _severity(delta_v_kmph, rollover)

    return {
        "peak_g": round(peak_g, 2),
        "delta_v_kmph": round(delta_v_kmph, 2),
        "pdof_deg": round(pdof_deg, 1),
        "impact_direction": impact_direction,
        "rollover": rollover,
        "max_roll_deg": round(max_roll, 1),
        "csi": round(csi, 1),
        "severity": severity,
        "peak_at_ms": peak_sample.timestamp_ms,
        "speed_at_impact_kmph": round(speed_before, 1),
    }


def _in_pulse(sample):
    """Only integrate where acceleration is clearly crash-level, to avoid
    accumulating normal-driving accel into delta-V."""
    return math.hypot(sample.accel_x_g, sample.accel_y_g) > 2.0


def _sector(angle_deg):
    """Map a force angle (0=front, 90=left, 180=rear, -90=right) to a name."""
    a = (angle_deg + 360) % 360
    sectors = [
        (22.5, "Frontal"),
        (67.5, "Front-Left"),
        (112.5, "Left"),
        (157.5, "Rear-Left"),
        (202.5, "Rear"),
        (247.5, "Rear-Right"),
        (292.5, "Right"),
        (337.5, "Front-Right"),
        (360.0, "Frontal"),
    ]
    for limit, name in sectors:
        if a < limit:
            return name
    return "Frontal"


def _severity(delta_v, rollover):
    if rollover:
        return "Severe"
    if delta_v >= config.DELTA_V_SEVERE_KMPH:
        return "Severe"
    if delta_v >= config.DELTA_V_MINOR_KMPH:
        return "Moderate"
    return "Minor"
