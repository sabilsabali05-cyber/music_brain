from __future__ import annotations

import json
from pathlib import Path

from scripts import generate_ratio_controlled_song as script


def test_generate_ratio_controlled_song_outputs_expected_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(script, "ROOT_DIR", tmp_path)
    assert script.main() == 0
    out_root = tmp_path / "outputs" / "ratio_controlled_song_v1"
    assert (out_root / "full.mid").exists()
    assert (out_root / "stems" / "chords.mid").exists()
    assert (out_root / "stems" / "bass.mid").exists()
    assert (out_root / "stems" / "lead.mid").exists()
    assert (out_root / "stems" / "texture.mid").exists()
    spec = json.loads((out_root / "ratio_control_spec.json").read_text(encoding="utf-8"))
    assert spec["evidence_based_only"] is True
    assert spec["no_cloud_calls"] is True
    explanation = (out_root / "ratio_explanation.md").read_text(encoding="utf-8")
    assert "Climax timing uses a golden-section anchor" in explanation

