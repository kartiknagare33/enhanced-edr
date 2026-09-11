"""
Real-hardware data source (Raspberry Pi 3B).

THIS IS THE ONLY FILE YOU WRITE WHEN HARDWARE ARRIVES. It presents the exact
same interface as SimulatedDataSource, so main.py swaps one for the other and
nothing else in the system changes.

Each read() must assemble one fully-populated EDRSample from:
    - CAN frames from the ESP32 via MCP2515 (SPI)   -> vehicle dynamics fields
    - MPU6050 over I2C                               -> IMU fields
    - NEO-6M over UART (NMEA)                        -> GPS fields
    - Voltage divider on a GPIO / ADC               -> supply_voltage_v, power_fail
    - RTC over I2C                                   -> rtc_epoch

The scaffolding below shows exactly where each driver plugs in. The imports are
deferred so this file can exist on a laptop without the Pi libraries installed.
"""

from .base import DataSource
from ..model import EDRSample
from .. import config


class HardwareDataSource(DataSource):
    def __init__(self):
        self._can = None
        self._imu = None
        self._gps = None
        self._rtc = None
        self._t0 = None

    def start(self):
        import time
        self._t0 = time.time()
        # --- TODO on Pi: initialise drivers ---
        # import can, board, busio, adafruit_mpu6050, serial, adafruit_gps
        # self._can = can.interface.Bus(channel="can0", bustype="socketcan")
        # i2c = busio.I2C(board.SCL, board.SDA)
        # self._imu = adafruit_mpu6050.MPU6050(i2c)
        # self._gps = adafruit_gps.GPS(serial.Serial("/dev/serial0", 9600))
        raise NotImplementedError(
            "HardwareDataSource is a scaffold. Implement the driver reads on the Pi. "
            "Until then, run with the simulated source."
        )

    def has_next(self):
        return True   # hardware streams forever

    def read(self) -> EDRSample:
        import time
        s = EDRSample()
        s.timestamp_ms = int((time.time() - self._t0) * 1000)

        # --- TODO: CAN -> vehicle dynamics ---
        # msg = self._can.recv(timeout=0.0)
        # parse frame IDs 0x100/0x101/0x200 into speed, brake, steering, crash flag...

        # --- TODO: IMU -> acceleration / gyro / attitude ---
        # ax, ay, az = self._imu.acceleration      # m/s^2
        # s.accel_x_g, s.accel_y_g, s.accel_z_g = ax/9.81, ay/9.81, az/9.81

        # --- TODO: GPS -> position / speed ---
        # self._gps.update(); s.latitude = self._gps.latitude ...

        # --- TODO: power sense (voltage divider -> ADC/GPIO) ---
        # s.supply_voltage_v = read_supply_voltage()
        # s.power_fail = s.supply_voltage_v < config.POWER_FAIL_VOLTAGE

        return s

    def stop(self):
        if self._can:
            self._can.shutdown()
