from __future__ import annotations

from features.beat_battle_agent.sound_pair_record_schema import SoundPairGenerationStatus, validate_generation_status


def test_generation_status_enum_matches_required_values() -> None:
    assert SoundPairGenerationStatus.generated.value == "generated"
    assert SoundPairGenerationStatus.pending_synplant_config.value == "pending_synplant_config"
    assert SoundPairGenerationStatus.failed.value == "failed"
    assert SoundPairGenerationStatus.skipped.value == "skipped"


def test_validate_generation_status_accepts_required_values_only() -> None:
    assert validate_generation_status("generated") == "generated"
    assert validate_generation_status("pending_synplant_config") == "pending_synplant_config"
    assert validate_generation_status("failed") == "failed"
    assert validate_generation_status("skipped") == "skipped"
