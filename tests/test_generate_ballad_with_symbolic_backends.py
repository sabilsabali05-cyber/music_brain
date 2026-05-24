from __future__ import annotations

import json
from pathlib import Path

from scripts import generate_2min_ballad


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_ballad_v2_fallback_when_no_backends(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        generate_2min_ballad,
        "evaluate_activation_status",
        lambda: {
            "text2midi_available": False,
            "moonbeam_available": False,
            "midigpt_available": False,
            "musicbert_available": False,
        },
    )
    report = generate_2min_ballad.generate_ballad_v2(tmp_path / "out", use_symbolic_backends=True)
    assert report["real_backend_generation"] is False
    assert report["real_backend_ranking"] is False
    assert report["fallback_used"] is True
    assert report["cloud_called"] is False
    assert report["trained_model_generation"] is False
    assert report["personal_model_training_used"] is False
    assert report["no_audio_processing"] is True


def test_ballad_v2_reports_used_backends_honestly(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        generate_2min_ballad,
        "evaluate_activation_status",
        lambda: {
            "text2midi_available": True,
            "moonbeam_available": True,
            "midigpt_available": False,
            "musicbert_available": True,
        },
    )
    output_dir = tmp_path / "out"
    report = generate_2min_ballad.generate_ballad_v2(output_dir, use_symbolic_backends=True)
    assert report["text2midi_used"] is True
    assert report["moonbeam_used"] is True
    assert report["midigpt_used"] is False
    assert report["musicbert_used"] is True
    assert report["real_backend_generation"] is True
    assert report["real_backend_ranking"] is True
    assert report["fallback_used"] is False

    generation_json = _read_json(output_dir / "generation_report.json")
    usage_json = _read_json(output_dir / "model_backend_usage_report.json")
    assert generation_json["text2midi_used"] is True
    assert usage_json["midigpt"]["used"] is False


def test_ballad_v2_outputs_required_files(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        generate_2min_ballad,
        "evaluate_activation_status",
        lambda: {
            "text2midi_available": False,
            "moonbeam_available": False,
            "midigpt_available": False,
            "musicbert_available": False,
        },
    )
    output_dir = tmp_path / "out"
    generate_2min_ballad.generate_ballad_v2(output_dir, use_symbolic_backends=True)
    required = [
        "ballad_full.mid",
        "ballad_drums.mid",
        "ballad_bass.mid",
        "ballad_chords.mid",
        "ballad_lead.mid",
        "ballad_texture.mid",
        "generation_report.md",
        "generation_report.json",
        "provenance_report.md",
        "provenance_report.json",
        "model_backend_usage_report.md",
        "model_backend_usage_report.json",
        "ableton_track_plan.md",
    ]
    for rel in required:
        assert (output_dir / rel).exists(), rel


def test_ballad_reports_do_not_leak_private_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        generate_2min_ballad,
        "evaluate_activation_status",
        lambda: {
            "text2midi_available": False,
            "moonbeam_available": False,
            "midigpt_available": False,
            "musicbert_available": False,
        },
    )
    output_dir = tmp_path / "out"
    generate_2min_ballad.generate_ballad_v2(output_dir, use_symbolic_backends=True)
    text = (output_dir / "generation_report.json").read_text(encoding="utf-8")
    assert ("C:/" + "Users/") not in text
    assert ("C:\\" + "Users\\") not in text
