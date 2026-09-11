import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from edr.core.ring_buffer import RingBuffer
from edr.model import EDRSample


class TestRingBuffer(unittest.TestCase):
    def _s(self, i):
        return EDRSample(timestamp_ms=i)

    def test_overwrites_oldest(self):
        buf = RingBuffer(size=100)
        for i in range(150):
            buf.push(self._s(i))
        self.assertEqual(len(buf), 100)
        # oldest retained should be sample 50
        self.assertEqual(buf.pre_window.__self__._buf[0].timestamp_ms, 50)

    def test_freeze_snapshots_and_splits(self):
        buf = RingBuffer(size=100)
        for i in range(100):
            buf.push(self._s(i))
        buf.freeze()
        # after freeze, pushes go to post-crash
        for i in range(100, 110):
            buf.push(self._s(i))
        self.assertEqual(len(buf.pre_window()), 100)
        self.assertEqual(buf.post_count(), 10)
        window = buf.window()
        self.assertEqual(len(window), 110)
        self.assertEqual(window[0].timestamp_ms, 0)
        self.assertEqual(window[-1].timestamp_ms, 109)

    def test_full_flag(self):
        buf = RingBuffer(size=5)
        for i in range(4):
            buf.push(self._s(i))
        self.assertFalse(buf.is_full)
        buf.push(self._s(4))
        self.assertTrue(buf.is_full)


if __name__ == "__main__":
    unittest.main()
