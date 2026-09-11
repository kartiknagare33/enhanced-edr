import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from edr.core.detector import CrashDetector
from edr.core.analytics import analyze, _sector
from edr.model import EDRSample
from edr import config


class TestDetector(unittest.TestCase):
    def test_no_trigger_on_calm(self):
        d = CrashDetector()
        for _ in range(10):
            r = d.update(EDRSample(speed_kmph=50, accel_x_g=0.1, accel_y_g=0.0))
            self.assertFalse(r.triggered)

    def test_g_spike_triggers(self):
        d = CrashDetector()
        d.update(EDRSample(speed_kmph=50))
        r = d.update(EDRSample(speed_kmph=50, accel_x_g=-10.0))
        self.assertTrue(r.triggered)
        self.assertTrue(any("G-spike" in x for x in r.reasons))

    def test_ecu_flag_triggers(self):
        d = CrashDetector()
        r = d.update(EDRSample(crash_flag_ecu=True))
        self.assertTrue(r.triggered)

    def test_power_fail_triggers(self):
        d = CrashDetector()
        r = d.update(EDRSample(power_fail=True))
        self.assertTrue(r.triggered)

    def test_debounce_blocks_retrigger(self):
        d = CrashDetector()
        d.update(EDRSample(speed_kmph=50))
        self.assertTrue(d.update(EDRSample(accel_x_g=-10.0)).triggered)
        # immediately after, should be debounced
        self.assertFalse(d.update(EDRSample(accel_x_g=-10.0)).triggered)


class TestAnalytics(unittest.TestCase):
    def _window(self, ax=0.0, ay=0.0, roll=0.0, speed=60.0):
        # a calm lead-in then one big spike sample
        w = [EDRSample(timestamp_ms=i * 10, speed_kmph=speed,
                       accel_x_g=0.1, accel_y_g=0.0) for i in range(20)]
        w.append(EDRSample(timestamp_ms=200, speed_kmph=speed - 30,
                           accel_x_g=ax, accel_y_g=ay, roll_deg=roll))
        return w

    def test_frontal_direction_recovered(self):
        # frontal impact -> negative ax -> force from the front
        res = analyze(self._window(ax=-25.0))
        self.assertEqual(res["impact_direction"], "Frontal")

    def test_rear_direction_recovered(self):
        res = analyze(self._window(ax=+25.0))
        self.assertEqual(res["impact_direction"], "Rear")

    def test_left_direction_recovered(self):
        res = analyze(self._window(ay=-25.0))
        self.assertEqual(res["impact_direction"], "Left")

    def test_rollover_flag(self):
        res = analyze(self._window(ax=-10.0, roll=70.0))
        self.assertTrue(res["rollover"])
        self.assertEqual(res["severity"], "Severe")

    def test_peak_g_and_csi(self):
        res = analyze(self._window(ax=-20.0))
        self.assertAlmostEqual(res["peak_g"], 20.0, delta=0.1)
        self.assertAlmostEqual(res["csi"], 50.0, delta=1.0)  # 20/40*100

    def test_sector_boundaries(self):
        self.assertEqual(_sector(0), "Frontal")
        self.assertEqual(_sector(90), "Left")
        self.assertEqual(_sector(180), "Rear")
        self.assertEqual(_sector(-90), "Right")


if __name__ == "__main__":
    unittest.main()
