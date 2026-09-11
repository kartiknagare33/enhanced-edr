"""
Central configuration for the Enhanced Event Data Recorder (eEDR).

Every tunable number in the system lives here, so behaviour can be changed
without touching logic. This is also where the 40-vs-28 parameter question is
resolved explicitly: the full model always carries 40 parameters, and
CRASH_CRITICAL_PARAMS defines the subset that gets locked into flash.
"""

# ---------------------------------------------------------------------------
# Sampling / buffer
# ---------------------------------------------------------------------------
SAMPLE_RATE_HZ = 100                     # high-rate buffering rate
BUFFER_WINDOW_S = 20                     # seconds of pre-crash history retained
BUFFER_SIZE = SAMPLE_RATE_HZ * BUFFER_WINDOW_S   # = 2000 samples
SAMPLE_PERIOD_S = 1.0 / SAMPLE_RATE_HZ

# Continuous long-term driving log (separate from crash capture)
SD_LOG_RATE_HZ = 1

# How long we keep recording AFTER a crash trigger, before finalizing
POST_CRASH_WINDOW_S = 5
POST_CRASH_SAMPLES = SAMPLE_RATE_HZ * POST_CRASH_WINDOW_S

# ---------------------------------------------------------------------------
# Crash-detection thresholds
# ---------------------------------------------------------------------------
# Net horizontal acceleration (gravity removed) above which we call it a crash.
# Typical airbag-deploy events are well above this.
CRASH_ACCEL_THRESHOLD_G = 4.0

# Sudden speed loss between consecutive samples that implies a crash-level
# deceleration (km/h lost in one 10 ms tick).
CRASH_SPEED_DELTA_KMPH = 2.5

# Roll angle beyond which a rollover is declared.
ROLLOVER_ANGLE_DEG = 45.0

# Supply voltage below which a power-fail event is asserted.
POWER_FAIL_VOLTAGE = 9.0

# Debounce: once triggered, ignore new triggers for this many samples.
TRIGGER_DEBOUNCE_SAMPLES = SAMPLE_RATE_HZ * 2   # 2 s

# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
# Reference peak acceleration mapped to Crash Severity Index = 100.
CSI_REFERENCE_G = 40.0

# Delta-V severity bands (km/h). Loosely follow real-world injury correlations.
DELTA_V_MINOR_KMPH = 16.0
DELTA_V_SEVERE_KMPH = 40.0

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
EVENTS_DIR = "events"                    # crash records live here
SD_LOG_FILE = "driving_log.csv"          # continuous log
FLASH_IMAGE = "flash_crash.json"         # simulated SPI-flash crash image
LOCK_FILE = "memory.lock"                # simulated hardware write-protect flag

# ---------------------------------------------------------------------------
# Crash-critical parameter subset (the data locked into flash).
# The full sample carries 40 fields; these are the forensically important ones.
# Edit this list to match whatever your report commits to.
# ---------------------------------------------------------------------------
CRASH_CRITICAL_PARAMS = [
    "timestamp_ms",
    "speed_kmph",
    "accel_pedal_pct",
    "brake_pedal_pct",
    "brake_active",
    "steering_angle_deg",
    "gear",
    "engine_rpm",
    "throttle_pct",
    "wheel_speed_fl",
    "wheel_speed_fr",
    "wheel_speed_rl",
    "wheel_speed_rr",
    "abs_active",
    "crash_flag_ecu",
    "accel_x_g",
    "accel_y_g",
    "accel_z_g",
    "gyro_x_dps",
    "gyro_y_dps",
    "gyro_z_dps",
    "roll_deg",
    "pitch_deg",
    "yaw_deg",
    "gps_speed_kmph",
    "seatbelt_driver",
    "supply_voltage_v",
    "power_fail",
]   # 28 parameters
