from __future__ import annotations

from scripts.train_battle_outcome_ranker import build_training_report


def test_training_report_uses_heuristic_below_20() -> None:
    payload = build_training_report(19)
    assert payload["training_mode"] == "heuristic_baseline"
    assert payload["battle_outcome_ranker_trained"] is False


def test_training_report_runs_holdout_at_50() -> None:
    payload = build_training_report(50)
    assert payload["training_mode"] == "local_train"
    assert payload["holdout_evaluation_ran"] is True
