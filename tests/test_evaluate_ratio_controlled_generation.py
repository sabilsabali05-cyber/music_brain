from __future__ import annotations

import json
from pathlib import Path

from scripts import evaluate_ratio_controlled_generation as eval_script
from scripts import generate_ratio_controlled_song as gen_script


def test_evaluate_ratio_controlled_generation_produces_compliance_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gen_script, "ROOT_DIR", tmp_path)
    assert gen_script.main() == 0
    monkeypatch.setattr(eval_script, "ROOT_DIR", tmp_path)
    assert eval_script.main() == 0
    report = json.loads(
        (tmp_path / "reports" / "ratio_understanding" / "ratio_controlled_generation_v2_eval.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["status"] == "ok"
    assert 0.0 <= float(report["ratio_compliance_score"]) <= 1.0
    assert report["ratio_controls_evaluated"] >= 1
    assert report["plan_used"] is not None
    assert "per_control_scores" in report
    assert "density_peak_time_seconds" in report


def test_golden_section_improves_against_known_v1_baseline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gen_script, "ROOT_DIR", tmp_path)
    assert gen_script.main() == 0
    monkeypatch.setattr(eval_script, "ROOT_DIR", tmp_path)
    assert eval_script.main() == 0
    report = json.loads(
        (tmp_path / "reports" / "ratio_understanding" / "ratio_controlled_generation_v2_eval.json").read_text(
            encoding="utf-8"
        )
    )
    golden = next(item for item in report["evaluations"] if item["ratio_name"] == "golden_section_0_618")
    v1_golden_error = abs(0.6862499276718008 - 0.61803398875)
    assert float(golden["absolute_error"]) <= v1_golden_error


def test_three_controls_or_blockers_reported(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gen_script, "ROOT_DIR", tmp_path)
    assert gen_script.main() == 0
    monkeypatch.setattr(eval_script, "ROOT_DIR", tmp_path)
    assert eval_script.main() == 0
    report = json.loads(
        (tmp_path / "reports" / "ratio_understanding" / "ratio_controlled_generation_v2_eval.json").read_text(
            encoding="utf-8"
        )
    )
    within = int(report["ratio_controls_within_tolerance"])
    if within < 3:
        assert any("low_ratio_compliance_score" in w or "missing_measurement" in w for w in report["warnings"])
    else:
        assert within >= 3

