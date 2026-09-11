"""
Scripted scenarios for the simulator.

A Scenario is a timeline: at any time t it returns the current driver inputs
(throttle/brake/steer) and any active events (impacts, rollover, power loss).
Each scenario tells a coherent story so the resulting telemetry — and the crash
report the EDR produces from it — is meaningful, not random.
"""


class Scenario:
    def __init__(self, name, duration_s, phases, events):
        self.name = name
        self.duration_s = duration_s
        self.phases = phases      # list of (t_start, t_end, inputs dict)
        self.events = events      # list of event dicts with a 't' key

    def inputs_at(self, t):
        current = {"throttle": 0.0, "brake": 0.0, "steer": 0.0}
        for t0, t1, inp in self.phases:
            if t0 <= t < t1:
                current = inp
        return current

    def events_at(self, t):
        active = []
        for ev in self.events:
            dur = ev.get("dur", ev.get("pulse_ms", 120) / 1000.0)
            if ev["t"] <= t <= ev["t"] + dur:
                active.append(ev)
        return active


def _cruise(throttle=0.35):
    return {"throttle": throttle, "brake": 0.0, "steer": 0.0}


# --- scenario library -------------------------------------------------------

def normal_drive():
    return Scenario(
        "normal_drive", duration_s=25,
        phases=[(0, 5, _cruise(0.6)), (5, 20, _cruise(0.3)), (20, 25, _cruise(0.4))],
        events=[],
    )


def hard_brake():
    return Scenario(
        "hard_brake", duration_s=20,
        phases=[(0, 8, _cruise(0.7)),
                (8, 14, {"throttle": 0.0, "brake": 0.9, "steer": 0.0}),
                (14, 20, _cruise(0.2))],
        events=[],   # hard braking but NOT a crash — tests that we don't false-trigger
    )


def frontal_collision():
    return Scenario(
        "frontal_collision", duration_s=18,
        phases=[(0, 10, _cruise(0.8)),
                (10, 12, {"throttle": 0.0, "brake": 1.0, "steer": 0.0})],
        events=[{"type": "impact", "t": 12.0, "axis": "front",
                 "peak_g": 30.0, "pulse_ms": 120}],
    )


def side_impact_left():
    return Scenario(
        "side_impact_left", duration_s=16,
        phases=[(0, 10, _cruise(0.5))],
        events=[{"type": "impact", "t": 10.0, "axis": "left",
                 "peak_g": 22.0, "pulse_ms": 100}],
    )


def rollover():
    return Scenario(
        "rollover", duration_s=16,
        phases=[(0, 9, _cruise(0.7)),
                (9, 11, {"throttle": 0.2, "brake": 0.0, "steer": 25.0})],
        events=[{"type": "impact", "t": 10.0, "axis": "right",
                 "peak_g": 12.0, "pulse_ms": 150},
                {"type": "rollover", "t": 10.0, "roll_deg": 70.0, "dur": 1.5}],
    )


def power_loss_during_crash():
    return Scenario(
        "power_loss_during_crash", duration_s=16,
        phases=[(0, 10, _cruise(0.8)),
                (10, 12, {"throttle": 0.0, "brake": 1.0, "steer": 0.0})],
        events=[{"type": "impact", "t": 11.0, "axis": "front",
                 "peak_g": 28.0, "pulse_ms": 120},
                {"type": "power_loss", "t": 11.1, "dur": 0.3}],
    )


ALL = {
    "normal_drive": normal_drive,
    "hard_brake": hard_brake,
    "frontal_collision": frontal_collision,
    "side_impact_left": side_impact_left,
    "rollover": rollover,
    "power_loss_during_crash": power_loss_during_crash,
}
