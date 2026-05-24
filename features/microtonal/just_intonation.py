from __future__ import annotations

import math


def ratio_to_float(value: str) -> float:
    text = value.strip()
    if "/" in text:
        num, den = text.split("/", 1)
        return float(num.strip()) / float(den.strip())
    return float(text)


def ratio_to_cents(value: str) -> float:
    ratio = ratio_to_float(value)
    if ratio <= 0:
        raise ValueError("ratio must be positive")
    return 1200.0 * math.log2(ratio)


def ratios_to_cents(ratios: list[str]) -> list[float]:
    return [round(ratio_to_cents(item), 6) for item in ratios]
