from __future__ import annotations

from typing import Any

EXPORT_STRATEGIES = [
    "standard_midi_pitch_bend",
    "multichannel_pitch_bend_midi",
    "mpe_midi",
    "scala_scl",
    "keyboard_mapping_kbm",
    "tuning_table_json",
    "ableton_max_tuning_bridge_plan",
    "rendered_audio_fallback_plan",
]


def requires_channel_split_or_mpe(*, strategy: str, polyphonic: bool) -> bool:
    return bool(polyphonic and strategy == "standard_midi_pitch_bend")


def build_microtonal_export_plan(*, strategy: str, polyphonic: bool) -> dict[str, Any]:
    if strategy not in EXPORT_STRATEGIES:
        raise ValueError(f"Unsupported export strategy: {strategy}")
    required = requires_channel_split_or_mpe(strategy=strategy, polyphonic=polyphonic)
    return {
        "status": "ok",
        "strategy": strategy,
        "polyphonic_input": polyphonic,
        "requires_channel_split_or_mpe": required,
        "recommended_path": "Use channel splitting or MPE." if required else "Direct strategy acceptable.",
        "no_audio_generated": True,
        "cloud_called": False,
        "training_performed": False,
    }
