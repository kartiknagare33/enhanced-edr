"""
Continuous driving logger (the SD card).

Independent of crash capture: it appends one row per second for the whole trip,
giving investigators the long-term context around any event. Writes the full
40-parameter sample as CSV.
"""

import csv
from ..model import EDRSample


class SDLogger:
    def __init__(self, path):
        self.path = path
        self._fields = EDRSample.field_names()
        self._fh = open(path, "w", newline="")
        self._writer = csv.DictWriter(self._fh, fieldnames=self._fields)
        self._writer.writeheader()
        self.rows = 0

    def log(self, sample):
        self._writer.writerow(sample.to_dict())
        self.rows += 1

    def close(self):
        self._fh.flush()
        self._fh.close()
