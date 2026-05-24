from __future__ import annotations

from pathlib import Path

from features.beat_battle_agent.sound_pair_record_schema import BattleSoundPairRecord
from features.beat_battle_agent.sound_pair_listening_sheet import write_listening_sheet


def test_write_listening_sheet_includes_required_fields_and_questions(tmp_path: Path) -> None:
    record = BattleSoundPairRecord(
        record_id="round_01:sound_001_synplant_001",
        round_id="round_01",
        created_at_utc="2026-05-24T00:00:00+00:00",
        source_round_manifest_path="datasets/beat_battle_site/rounds/round_01/round_manifest.json",
        provided_sound_id="sound_001",
        provided_source_kind="manual_file_import",
        provided_source_ref="<LOCAL_AUDIO_PATH>",
        provided_original_path="C:/tmp/source.wav",
        provided_local_copy_path="local_battle_records/round_01/provided_sounds/sound_001.wav",
        provided_audio_readable=True,
        synplant_variation_id="sound_001_synplant_001",
        synplant_generation_status="pending_synplant_config",
        synplant_blocker="synplant_not_configured",
        synplant_task_created=True,
        synplant_variation_path="local_battle_records/round_01/synplant_variations/sound_001_synplant_001.wav",
        synplant_variation_exists=False,
        synplant_variation_non_silent=False,
        listening_sheet_md_path="local_battle_records/round_01/listening_sheet.md",
        listening_sheet_html_path="local_battle_records/round_01/listening_sheet.html",
        review_notes_local_json_path="local_battle_records/round_01/review_notes.local.json",
        listening_questions=[
            "Which version wins for this battle sound pair? (provided/synplant/tie/skip)",
            "How well does the Synplant variation preserve core character? (1-5)",
        ],
    )

    html_path = tmp_path / "listening_sheet.html"
    md_path = tmp_path / "listening_sheet.md"
    review_notes_path = tmp_path / "review_notes.local.json"
    write_listening_sheet([record], html_path=html_path, md_path=md_path, review_notes_path=review_notes_path)

    md_text = md_path.read_text(encoding="utf-8")
    html_text = html_path.read_text(encoding="utf-8")
    review_text = review_notes_path.read_text(encoding="utf-8")
    assert "sound_001_synplant_001" in md_text
    assert "generation_status" in md_text
    assert "Which version wins for this battle sound pair?" in md_text
    assert "<table" in html_text
    assert "provided_sound_id" in html_text
    assert "reviews" in review_text
