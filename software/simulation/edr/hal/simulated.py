"""
Physics-based driving + crash simulator.

This is not a random-number generator. It runs a simple longitudinal/lateral
vehicle model driven by scripted driver inputs, and injects physically-shaped
crash pulses. The 40-parameter telemetry it emits is internally consistent:
wheel speeds track vehicle speed, IMU acceleration follows from the dynamics,
GPS integrates position, and a frontal impact really does show up as a negative
accel_x pulse — which the analytics engine later recovers as "Frontal".

A Scenario is a timeline of driver inputs and events (see scenarios.py).
"""

import math
import random
from .base import DataSource
from ..model import EDRSample
from .. import config

G = 9.81  # m/s^2


class SimulatedDataSource(DataSource):
    def __init__(self, scenario, seed: int = 42, noise: float = 1.0):
        """
        scenario : a Scenario object with .duration_s and .inputs_at(t)/.events_at(t)
        noise    : multiplier on sensor noise (0 = clean, 1 = realistic)
        """
        self.scenario = scenario
        self.rng = random.Random(seed)
        self.noise = noise

        # Vehicle state
        self.t = 0.0
        self.speed = 0.0            # m/s (longitudinal)
        self.heading = 0.0          # deg
        self.yaw_rate = 0.0         # deg/s
        self.roll = 0.0             # deg
        self.pitch = 0.0            # deg
        self.pos_lat = 19.0760      # start near Mumbai
        self.pos_lon = 72.8777
        self.distance = 0.0

        # Instantaneous accelerations felt by the IMU (m/s^2)
        self._ax = 0.0
        self._ay = 0.0
        self._az_extra = 0.0

        # Power state
        self.supply_v = 12.0
        self.supercap_v = 5.0

        self._n = 0
        self._prev_speed = 0.0

    # -- DataSource interface -------------------------------------------------
    def start(self):
        self.t = 0.0

    def has_next(self):
        return self.t < self.scenario.duration_s

    def stop(self):
        pass

    # -- Core step ------------------------------------------------------------
    def read(self) -> EDRSample:
        dt = config.SAMPLE_PERIOD_S
        inp = self.scenario.inputs_at(self.t)
        events = self.scenario.events_at(self.t)

        # ----- driver inputs -> longitudinal dynamics -----
        throttle = inp.get("throttle", 0.0)          # 0..1
        brake = inp.get("brake", 0.0)                # 0..1
        steer = inp.get("steer", 0.0)                # deg

        # Simple force model: engine push, braking, aero+roll drag.
        drive_acc = throttle * 3.5                    # m/s^2 max ~0.35g accel
        brake_acc = brake * 8.0                       # m/s^2 max ~0.8g braking
        drag = 0.02 * self.speed + 0.3                # rolling + aero
        long_acc = drive_acc - brake_acc - (drag if self.speed > 0 else 0)

        # ----- crash / event injection -----
        crash_flag = False
        power_fail = False
        impact_ax = impact_ay = 0.0   # set directly (not accumulated) from the pulse
        for ev in events:
            kind = ev["type"]
            if kind == "impact":
                # A shaped deceleration pulse along a body axis.
                # axis: 'front','rear','left','right'; peak in g; over pulse_ms.
                pulse = _impact_pulse(ev, self.t)
                impact_ax += pulse[0]
                impact_ay += pulse[1]
                if pulse[2]:
                    crash_flag = True
                    # a real impact also sheds vehicle speed rapidly
                    self.speed = max(0.0, self.speed - (abs(pulse[0]) * dt))
            elif kind == "rollover":
                # Ramp roll angle past the rollover threshold.
                self.roll = ev["roll_deg"] * _ramp(ev, self.t)
            elif kind == "power_loss":
                # Collapse the supply; supercap begins to sag.
                self.supply_v = 5.0 * (1 - _ramp(ev, self.t))
                self.supercap_v = max(3.0, 5.0 - 2.0 * _ramp(ev, self.t))
                if self.supply_v < config.POWER_FAIL_VOLTAGE:
                    power_fail = True

        # Integrate longitudinal motion (don't let speed go negative).
        self.speed = max(0.0, self.speed + long_acc * dt)

        # Lateral dynamics from steering (very simplified bicycle-ish model).
        # Yaw rate proportional to steer and speed.
        self.yaw_rate = steer * 0.05 * min(self.speed, 30.0)
        self.heading = (self.heading + self.yaw_rate * dt) % 360.0
        lateral_acc = math.radians(self.yaw_rate) * self.speed   # a = w * v

        # ----- assemble IMU accelerations (in g) -----
        # Base longitudinal accel felt (proper accel), plus the impact pulse.
        ax_g = (long_acc + impact_ax) / G
        ay_g = (lateral_acc + impact_ay) / G
        az_g = 1.0 + self._az_extra / G           # gravity + vertical shocks

        # Add tilt contribution to accel from roll/pitch (gravity projection).
        ax_g += math.sin(math.radians(self.pitch))
        ay_g += -math.sin(math.radians(self.roll))

        self._az_extra *= 0.55

        # ----- noise -----
        n = self.noise
        ax_g += self._noise(0.02 * n)
        ay_g += self._noise(0.02 * n)
        az_g += self._noise(0.02 * n)

        # ----- GPS integration -----
        self.distance += self.speed * dt
        # crude lat/lon drift along heading
        dlat = (self.speed * dt) * math.cos(math.radians(self.heading)) / 111_000.0
        dlon = (self.speed * dt) * math.sin(math.radians(self.heading)) / 111_000.0
        self.pos_lat += dlat
        self.pos_lon += dlon

        speed_kmph = self.speed * 3.6
        wheel = speed_kmph + self._noise(0.3 * n)

        # ABS engages under hard braking
        abs_active = brake > 0.6 and self.speed > 2.0

        sample = EDRSample(
            timestamp_ms=int(self.t * 1000),
            speed_kmph=round(speed_kmph, 2),
            accel_pedal_pct=round(throttle * 100, 1),
            brake_pedal_pct=round(brake * 100, 1),
            brake_active=brake > 0.05,
            steering_angle_deg=round(steer, 1),
            gear="D" if self.speed > 0.1 else "P",
            engine_rpm=round(900 + throttle * 4500 + speed_kmph * 25, 0),
            throttle_pct=round(throttle * 100, 1),
            wheel_speed_fl=round(wheel, 2),
            wheel_speed_fr=round(wheel, 2),
            wheel_speed_rl=round(wheel + self._noise(0.2 * n), 2),
            wheel_speed_rr=round(wheel + self._noise(0.2 * n), 2),
            abs_active=abs_active,
            tcs_active=throttle > 0.8 and self.speed < 5.0,
            crash_flag_ecu=crash_flag,
            seatbelt_driver=True,
            accel_x_g=round(ax_g, 3),
            accel_y_g=round(ay_g, 3),
            accel_z_g=round(az_g, 3),
            gyro_x_dps=round(self._noise(0.5 * n), 2),
            gyro_y_dps=round(self._noise(0.5 * n), 2),
            gyro_z_dps=round(self.yaw_rate, 2),
            roll_deg=round(self.roll, 2),
            pitch_deg=round(self.pitch, 2),
            yaw_deg=round(self.heading, 2),
            latitude=round(self.pos_lat, 6),
            longitude=round(self.pos_lon, 6),
            gps_speed_kmph=round(speed_kmph + self._noise(0.5 * n), 2),
            heading_deg=round(self.heading, 1),
            altitude_m=round(11.0 + self._noise(0.5 * n), 1),
            gps_fix=3,
            satellites=self.rng.randint(8, 12),
            supply_voltage_v=round(self.supply_v + self._noise(0.05 * n), 2),
            rail_5v_v=5.1,
            supercap_voltage_v=round(self.supercap_v, 2),
            power_fail=power_fail,
            cpu_temp_c=round(45 + self._noise(0.5 * n), 1),
            rtc_epoch=1_750_000_000 + int(self.t),
            fault_flags=0,
        )

        self._prev_speed = speed_kmph
        self.t += dt
        self._n += 1
        return sample

    def _noise(self, sigma):
        return self.rng.gauss(0, sigma) if self.noise > 0 else 0.0


# ---------------------------------------------------------------------------
# Event shaping helpers
# ---------------------------------------------------------------------------
def _ramp(ev, t):
    """0..1 linear ramp across the event window."""
    start = ev["t"]
    dur = ev.get("dur", 0.5)
    if t <= start:
        return 0.0
    if t >= start + dur:
        return 1.0
    return (t - start) / dur


def _impact_pulse(ev, t):
    """
    Return (ax, ay, crash_flag) in m/s^2 for an impact event, shaped as a short
    half-sine deceleration pulse. Sign convention: a frontal hit decelerates the
    car -> negative ax.
    """
    start = ev["t"]
    pulse_ms = ev.get("pulse_ms", 120)
    dur = pulse_ms / 1000.0
    if t < start or t > start + dur:
        return (0.0, 0.0, False)

    phase = (t - start) / dur
    shape = math.sin(math.pi * phase)          # 0 -> 1 -> 0
    peak = ev["peak_g"] * G
    axis = ev["axis"]

    ax = ay = 0.0
    if axis == "front":
        ax = -peak * shape
    elif axis == "rear":
        ax = +peak * shape
    elif axis == "left":
        ay = -peak * shape
    elif axis == "right":
        ay = +peak * shape
    return (ax, ay, True)
