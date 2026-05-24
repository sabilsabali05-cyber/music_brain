from __future__ import annotations

import json
from pathlib import Path

from scripts.generate_from_theory_conditioning import main as generate_main


def test_theory_conditioned_generation_outputs_and_policy_flags(tmp_path: Path, monkeypatch) -> None:
    profiles_path = tmp_path / "datasets" / "music_theory" / "generation_conditioning_profiles.jsonl"
    profiles_path.parent.mkdir(parents=True, exist_ok=True)
    profiles_path.write_text(
        json.dumps(
            {
                "profile_name": "harmony_first_ballad",
                "target_tempo_range": [72, 84],
                "chord_movement_strategy": "functional",
                "rhythm_strategy": "pocket",
                "preserve_list": [],
            }
        )
        + "\n"
        + json.dumps({"profile_name": "weird_but_musical_chromatic_motion", "target_tempo_range": [84, 96], "preserve_list": ["color"]})
        + "\n"
        + json.dumps({"profile_name": "dense_experimental_rhythm", "target_tempo_range": [96, 120], "rhythm_strategy": "dense"})
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert generate_main() == 0
    out = tmp_path / "outputs" / "theory_conditioned_generation_v1"
    assert (out / "harmony_first_piano_skeleton.mid").exists()
    report = json.loads((out / "generation_report.json").read_text(encoding="utf-8"))
    assert report["cloud_called"] is False
    assert report["model_training_used"] is False
    assert report["fake_model_usage_claimed"] is False
