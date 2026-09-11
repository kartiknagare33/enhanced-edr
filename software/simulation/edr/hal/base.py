"""
Hardware Abstraction Layer (HAL) — the single seam between the EDR core and
the outside world.

The recorder pulls samples through this interface and nothing else. Swapping
from simulation to real hardware means providing a different DataSource; the
buffer, detector, analytics and storage never change. That hardware-independence
is the central architectural claim of this project.
"""

from abc import ABC, abstractmethod
from ..model import EDRSample


class DataSource(ABC):
    """Abstract source of EDR samples."""

    @abstractmethod
    def start(self) -> None:
        """Initialise the source (open sensors, start the sim clock, etc.)."""

    @abstractmethod
    def read(self) -> EDRSample:
        """Return the next fully-populated 40-parameter sample."""

    @abstractmethod
    def has_next(self) -> bool:
        """True while more samples are available (finite for scripted sims)."""

    def stop(self) -> None:
        """Release any resources. Optional to override."""
