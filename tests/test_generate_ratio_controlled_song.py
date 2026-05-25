from __future__ import annotations

import json
from pathlib import Path

from mido import MidiFile

from scripts import generate_ratio_controlled_song as script


def test_generate_ratio_controlled_song_outputs_expected_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(script, "ROOT_DIR", tmp_path)
    assert script.main() == 0
    out_root = tmp_path / "outputs" / "ratio_controlled_song_v2"
    assert (out_root / "full.mid").exists()
    assert (out_root / "stems" / "chords.mid").exists()
    assert (out_root / "stems" / "bass.mid").exists()
    assert (out_root / "stems" / "lead.mid").exists()
    assert (out_root / "stems" / "texture.mid").exists()
    assert (out_root / "ratio_plan.json").exists()
    assert (out_root / "ratio_plan.md").exists()
    parsed = MidiFile((out_root / "full.mid").as_posix())
    assert len(parsed.tracks) >= 1
    spec = json.loads((out_root / "ratio_control_spec.json").read_text(encoding="utf-8"))
    assert spec["evidence_based_only"] is True
    assert spec["no_cloud_calls"] is True
    assert spec["generation_id"] == "ratio_controlled_song_v2"
    plan = json.loads((out_root / "ratio_plan.json").read_text(encoding="utf-8"))
    controls = plan["controls"]
    assert controls["golden_section_0_618"]["target"] == spec["ratio_controls"][0]["target_ratio"]
    assert controls["3:2"]["target"] == 1.5
    assert controls["5:3"]["target"] == 5.0 / 3.0
    assert controls["5:4"]["target"] == 1.25
    assert controls["8:5"]["target"] == 1.6
    explanation = (out_root / "ratio_explanation.md").read_text(encoding="utf-8")
    assert "golden-section control is tied to strongest density peak timing" in explanation

