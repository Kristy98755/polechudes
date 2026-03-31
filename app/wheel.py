from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Literal


WheelKind = Literal["points", "bankrupt", "pass", "prize", "x2", "x3", "plus"]


@dataclass(frozen=True)
class WheelSector:
    label: str
    kind: WheelKind
    value: int = 0


def default_sectors() -> list[WheelSector]:
    # Not a perfect copy of any single season; provides familiar set.
    # You can later tweak to match a specific year visually/semantically.
    return [
        WheelSector("200", "points", 200),
        WheelSector("300", "points", 300),
        WheelSector("400", "points", 400),
        WheelSector("500", "points", 500),
        WheelSector("БАНКРОТ", "bankrupt", 0),
        WheelSector("600", "points", 600),
        WheelSector("0", "pass", 0),
        WheelSector("700", "points", 700),
        WheelSector("ПРИЗ", "prize", 0),
        WheelSector("800", "points", 800),
        WheelSector("x2", "x2", 2),
        WheelSector("900", "points", 900),
        WheelSector("+", "plus", 0),
        WheelSector("1000", "points", 1000),
        WheelSector("x3", "x3", 3),
        WheelSector("200", "points", 200),
        WheelSector("300", "points", 300),
        WheelSector("400", "points", 400),
    ]


class WheelSpin:
    def __init__(self, sectors: list[WheelSector]) -> None:
        self.sectors = sectors
        self.angle: float = 0.0  # radians, 0..2pi
        self.omega: float = 0.0  # angular velocity
        self._running: bool = False
        self._on_stop: Callable[[WheelSector], None] | None = None

    @property
    def running(self) -> bool:
        return self._running

    def start(self, on_stop: Callable[[WheelSector], None] | None = None) -> None:
        if self._running:
            return
        self._running = True
        self._on_stop = on_stop
        self.omega = random.uniform(9.0, 13.0)  # fast start

    def emergency_stop(self) -> WheelSector:
        self._running = False
        self.omega = 0.0
        sector = self.current_sector()
        if self._on_stop:
            self._on_stop(sector)
        return sector

    def step(self, dt: float) -> WheelSector | None:
        if not self._running:
            return None

        self.angle = (self.angle + self.omega * dt) % (2 * math.pi)

        # friction
        self.omega *= (0.985 ** (dt * 60))
        if self.omega < 0.35:
            self._running = False
            self.omega = 0.0
            sector = self.current_sector()
            if self._on_stop:
                self._on_stop(sector)
            return sector

        return None

    def current_sector(self) -> WheelSector:
        n = len(self.sectors)
        if n == 0:
            raise ValueError("No sectors")
        # pointer at "top center" -> map angle to sector index
        # angle=0 means sector 0 centered at pointer.
        frac = (self.angle / (2 * math.pi)) % 1.0
        idx = int(round(frac * n)) % n
        return self.sectors[idx]

