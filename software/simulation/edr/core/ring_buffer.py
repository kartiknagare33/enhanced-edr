"""
Fixed-size circular (ring) buffer holding the most recent BUFFER_SIZE samples.

During normal driving it silently overwrites the oldest sample as each new one
arrives, so it always holds exactly the last BUFFER_WINDOW_S seconds of history
at zero storage cost. On a crash it is *frozen*: a snapshot of the pre-crash
window is taken, and post-crash samples are appended separately so the complete
event (before + after) can be analysed and stored.
"""

from collections import deque
from .. import config


class RingBuffer:
    def __init__(self, size: int = config.BUFFER_SIZE):
        self.size = size
        self._buf = deque(maxlen=size)
        self.frozen = False
        self._pre = []        # snapshot of pre-crash window
        self._post = []       # post-crash samples

    def push(self, sample):
        """Add a sample. Before freeze -> ring. After freeze -> post-crash list."""
        if not self.frozen:
            self._buf.append(sample)
        else:
            self._post.append(sample)

    def freeze(self):
        """Capture the current window as the pre-crash history."""
        self.frozen = True
        self._pre = list(self._buf)

    @property
    def is_full(self):
        return len(self._buf) == self.size

    def post_count(self):
        return len(self._post)

    def window(self):
        """Full event window: pre-crash history followed by post-crash samples."""
        return self._pre + self._post

    def pre_window(self):
        return list(self._pre)

    def latest(self):
        return self._buf[-1] if self._buf else None

    def __len__(self):
        return len(self._buf)
