from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.local_rendering.chordpotion_training_schema import load_training_rows  # noqa: E402


def main() -> int:
    dataset_path = ROOT_DIR / "datasets" / "chordpotion" / "chordpotion_audition_outcomes.jsonl"
    rows = load_training_rows(dataset_path)
    labeled = [row for row in rows if row.final_label.strip()]
    training_examples_count = len(labeled)

    artifact_dir = ROOT_DIR / "artifacts" / "model_training" / "chordpotion_preset_selector"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    report_dir = ROOT_DIR / "reports" / "model_training"
    report_dir.mkdir(parents=True, exist_ok=True)

    trained_selector_used = training_examples_count >= 20
    model_path = artifact_dir / "model.json"
    heuristic_or_trained = "trained_selector" if trained_selector_used else "heuristic_baseline"

    payload: dict = {
        "heuristic_or_trained": heuristic_or_trained,
        "training_examples_count": training_examples_count,
        "allowed_data_policy": "local_generated_midi_and_user_feedback_only",
    }
    if trained_selector_used:
        scores = defaultdict(list)
        for row in labeled:
            label = row.final_label.lower()
            if label in {"keep", "good", "reuse"}:
                numeric = 1.0
            elif label in {"reject", "bad"}:
                numeric = 0.0
            else:
                numeric = max(0.0, min(1.0, row.user_rating / 10.0))
            scores[row.preset_id].append(numeric)
        payload["preset_scores"] = {key: sum(values) / len(values) for key, values in scores.items()}
        model_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    else:
        payload["reason"] = "fewer_than_20_labeled_outcomes"
        model_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    training_report = ROOT_DIR / "reports" / "model_training" / "chordpotion_preset_selector_training_report.md"
    training_report.write_text(
        "\n".join(
            [
                "# ChordPotion Preset Selector Training Report",
                "",
                f"- training_examples_count: `{training_examples_count}`",
                f"- heuristic_or_trained: `{heuristic_or_trained}`",
                f"- trained_selector_used: `{str(trained_selector_used).lower()}`",
                "- training_policy: `local_generated_midi_plus_local_feedback_only`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"TRAINING_EXAMPLES_COUNT={training_examples_count}")
    print(f"HEURISTIC_OR_TRAINED={heuristic_or_trained}")
    print(f"TRAINED_SELECTOR_USED={str(trained_selector_used).lower()}")
    print(f"MODEL_PATH={model_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
