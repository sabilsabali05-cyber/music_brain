from __future__ import annotations

from pathlib import Path

from features.local_rendering.chordpotion_training_schema import load_training_rows


def test_training_dataset_policy_and_shape() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    dataset = repo_root / "datasets" / "chordpotion" / "chordpotion_audition_outcomes.jsonl"
    rows = load_training_rows(dataset)
    assert rows
    row = rows[0]
    assert row.provenance.get("policy") == "authorized_local_only"
    assert "input_harmony_features" in row.as_dict()
    assert "transformed_output_features" in row.as_dict()
