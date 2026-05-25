from __future__ import annotations

import json
from pathlib import Path

from scripts import evaluate_ratio_controlled_generation as eval_script
from scripts import generate_ratio_controlled_song as gen_script
from scripts import repair_ratio_controlled_generation as repair_script


def test_repair_loop_runs_and_writes_reports(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gen_script, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(eval_script, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(repair_script, "ROOT_DIR", tmp_path)
    assert gen_script.main() == 0
    assert eval_script.main() == 0
    assert repair_script.main() == 0
    report_path = tmp_path / "reports" / "ratio_understanding" / "ratio_repair_report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["guardrails"]["max_attempts"] == 3
    assert "fake_pass_prevention" in report["guardrails"]
    repaired_midi = tmp_path / "outputs" / "ratio_controlled_song_v2_repaired" / "full.mid"
    assert repaired_midi.exists()


def test_repair_loop_cannot_fake_success_by_editing_eval(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gen_script, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(eval_script, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(repair_script, "ROOT_DIR", tmp_path)
    assert gen_script.main() == 0
    assert eval_script.main() == 0
    fake_eval = tmp_path / "reports" / "ratio_understanding" / "ratio_controlled_generation_v2_eval.json"
    fake_eval.write_text('{"ratio_compliance_score": 1.0, "warnings": []}\n', encoding="utf-8")
    assert repair_script.main() == 0
    repaired_eval = json.loads(
        (tmp_path / "reports" / "ratio_understanding" / "ratio_controlled_generation_v2_repaired_eval.json").read_text(
            encoding="utf-8"
        )
    )
    assert repaired_eval.get("status") == "ok"
    assert repaired_eval.get("ratio_controls_evaluated", 0) >= 1


def test_musicality_warning_preserved_when_too_rigid(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gen_script, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(eval_script, "ROOT_DIR", tmp_path)
    assert gen_script.main() == 0
    plan_path = tmp_path / "outputs" / "ratio_controlled_song_v2" / "ratio_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    boundaries = [round(i * 1.5, 3) for i in range(0, 90)]
    plan["pre_generation_plan"]["phrase_grid"]["phrase_boundaries_seconds"] = boundaries
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    assert eval_script.main() == 0
    report = json.loads(
        (tmp_path / "reports" / "ratio_understanding" / "ratio_controlled_generation_v2_eval.json").read_text(
            encoding="utf-8"
        )
    )
    assert "too_rigid_phrase_grid" in report["warnings"]
