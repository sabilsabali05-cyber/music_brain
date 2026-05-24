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
        (tmp_path / "reports" / "ratio_understanding" / "ratio_controlled_generation_eval.json").read_text(encoding="utf-8")
    )
    assert report["status"] == "ok"
    assert 0.0 <= float(report["ratio_compliance_score"]) <= 1.0
    assert report["ratio_controls_evaluated"] >= 1

