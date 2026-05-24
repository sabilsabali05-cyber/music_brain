from __future__ import annotations

from .edo import edo_intervals_cents
from .just_intonation import ratios_to_cents
from .tuning_schema import TuningPreset

SUPPORTED_TUNING_PRESETS = [
    "12_tet",
    "19_edo",
    "22_edo",
    "24_edo",
    "31_edo",
    "53_edo",
    "just_major_5_limit",
    "just_minor_5_limit",
    "blues_leaning_microtonal",
    "pelog_placeholder",
    "slendro_placeholder",
    "maqam_placeholder",
    "raga_shruti_placeholder",
]

_A = "Placeholder-safe only; not ethnomusicological authority."
_REGISTRY: dict[str, TuningPreset] = {
    "12_tet": TuningPreset("12_tet", "edo", "12 equal divisions.", edo_intervals_cents(12), 12),
    "19_edo": TuningPreset("19_edo", "edo", "19 equal divisions.", edo_intervals_cents(19), 19),
    "22_edo": TuningPreset("22_edo", "edo", "22 equal divisions.", edo_intervals_cents(22), 22),
    "24_edo": TuningPreset("24_edo", "edo", "24 equal divisions.", edo_intervals_cents(24), 24),
    "31_edo": TuningPreset("31_edo", "edo", "31 equal divisions.", edo_intervals_cents(31), 31),
    "53_edo": TuningPreset("53_edo", "edo", "53 equal divisions.", edo_intervals_cents(53), 53),
    "just_major_5_limit": TuningPreset("just_major_5_limit", "just_intonation", "5-limit major set.", ratios_to_cents(["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"]), 7),
    "just_minor_5_limit": TuningPreset("just_minor_5_limit", "just_intonation", "5-limit minor set.", ratios_to_cents(["1/1", "9/8", "6/5", "4/3", "3/2", "8/5", "9/5"]), 7),
    "blues_leaning_microtonal": TuningPreset("blues_leaning_microtonal", "custom", "Blue-note leaning custom set.", [0.0, 170.0, 315.0, 386.314, 498.045, 701.955, 814.0, 1017.0], 8),
    "pelog_placeholder": TuningPreset("pelog_placeholder", "placeholder", "Placeholder pelog.", [0.0, 150.0, 320.0, 540.0, 700.0, 860.0, 1040.0], 7, True, _A),
    "slendro_placeholder": TuningPreset("slendro_placeholder", "placeholder", "Placeholder slendro.", [0.0, 240.0, 480.0, 720.0, 960.0], 5, True, _A),
    "maqam_placeholder": TuningPreset("maqam_placeholder", "placeholder", "Placeholder maqam.", [0.0, 150.0, 350.0, 500.0, 700.0, 850.0, 1050.0], 7, True, _A),
    "raga_shruti_placeholder": TuningPreset("raga_shruti_placeholder", "placeholder", "Placeholder raga/shruti.", [0.0, 90.0, 182.0, 294.0, 386.0, 498.0, 590.0, 702.0, 792.0, 906.0, 996.0, 1088.0], 12, True, _A),
}


def get_tuning_preset(preset_id: str) -> TuningPreset:
    if preset_id not in _REGISTRY:
        raise KeyError(f"Unsupported tuning preset: {preset_id}")
    return _REGISTRY[preset_id]
