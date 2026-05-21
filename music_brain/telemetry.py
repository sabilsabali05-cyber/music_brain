from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter
from typing import Iterator


@dataclass
class StageTimer:
    durations: dict[str, float] = field(default_factory=dict)
    _started_at: float = field(default_factory=perf_counter)

    @contextmanager
    def measure(self, stage: str) -> Iterator[None]:
        stage_started = perf_counter()
        try:
            yield
        finally:
            self.durations[stage] = perf_counter() - stage_started

    def total_seconds(self) -> float:
        return perf_counter() - self._started_at
