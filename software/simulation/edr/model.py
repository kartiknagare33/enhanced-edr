"""
The 40-parameter EDR data sample.

One EDRSample is the complete snapshot of the vehicle at one instant. The core
of the system only ever deals in EDRSample objects; it does not care whether
they came from the simulator or from real hardware.

Coordinate convention (SAE-style, right-handed):
    +x = forward,  +y = left,  +z = up
    A frontal impact decelerates the car, so the accelerometer reads a large
    NEGATIVE accel_x. Analytics inverts this to recover the impact direction.
"""

from dataclasses import dataclass, field, asdict, fields


@dataclass
class EDRSample:
    # --- Vehicle dynamics (from CAN: ECU frames 0x100/0x101/0x200) -----------
    timestamp_ms: int = 0            # 1  monotonic time since boot
    speed_kmph: float = 0.0          # 2
    accel_pedal_pct: float = 0.0     # 3
    brake_pedal_pct: float = 0.0     # 4
    brake_active: bool = False       # 5
    steering_angle_deg: float = 0.0  # 6
    gear: str = "P"                  # 7  P/R/N/D
    engine_rpm: float = 0.0          # 8
    throttle_pct: float = 0.0        # 9
    wheel_speed_fl: float = 0.0      # 10
    wheel_speed_fr: float = 0.0      # 11
    wheel_speed_rl: float = 0.0      # 12
    wheel_speed_rr: float = 0.0      # 13
    abs_active: bool = False         # 14
    tcs_active: bool = False         # 15
    crash_flag_ecu: bool = False     # 16  ECU-declared crash
    seatbelt_driver: bool = True     # 17  restraint status

    # --- IMU (MPU6050) -------------------------------------------------------
    accel_x_g: float = 0.0           # 18
    accel_y_g: float = 0.0           # 19
    accel_z_g: float = 1.0           # 20  ~1 g at rest (gravity)
    gyro_x_dps: float = 0.0          # 21
    gyro_y_dps: float = 0.0          # 22
    gyro_z_dps: float = 0.0          # 23
    roll_deg: float = 0.0            # 24
    pitch_deg: float = 0.0           # 25
    yaw_deg: float = 0.0             # 26

    # --- GPS (NEO-6M) --------------------------------------------------------
    latitude: float = 0.0            # 27
    longitude: float = 0.0           # 28
    gps_speed_kmph: float = 0.0      # 29
    heading_deg: float = 0.0         # 30
    altitude_m: float = 0.0          # 31
    gps_fix: int = 3                 # 32  0 none / 1 2D / 2 3D / 3 DGPS
    satellites: int = 9              # 33

    # --- System / power ------------------------------------------------------
    supply_voltage_v: float = 12.0   # 34  vehicle supply (12 V nominal)
    rail_5v_v: float = 5.1           # 35  regulated rail
    supercap_voltage_v: float = 5.0  # 36  backup bank
    power_fail: bool = False         # 37
    cpu_temp_c: float = 45.0         # 38
    rtc_epoch: int = 0               # 39  absolute time backup
    fault_flags: int = 0             # 40  bitfield of subsystem faults

    def to_dict(self) -> dict:
        return asdict(self)

    def subset(self, keys) -> dict:
        d = self.to_dict()
        return {k: d[k] for k in keys}

    @staticmethod
    def field_names():
        return [f.name for f in fields(EDRSample)]


assert len(EDRSample.field_names()) == 40, "EDRSample must carry exactly 40 parameters"
