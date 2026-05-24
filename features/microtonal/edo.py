from __future__ import annotations


def edo_step_cents(steps_per_octave: int) -> float:
    if steps_per_octave <= 0:
        raise ValueError("steps_per_octave must be positive")
    return 1200.0 / float(steps_per_octave)


def edo_intervals_cents(steps_per_octave: int) -> list[float]:
    step = edo_step_cents(steps_per_octave)
    return [round(step * idx, 6) for idx in range(steps_per_octave)]
