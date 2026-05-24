from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.local_rendering.chordpotion_training_schema import load_training_rows  # noqa: E402


def main() -> int:
    dataset_path = ROOT_DIR / "datasets" / "chordpotion" / "chordpotion_audition_outcomes.jsonl"
    model_path = ROOT_DIR / "artifacts" / "model_training" / "chordpotion_preset_selector" / "model.json"
    rows = [row for row in load_training_rows(dataset_path) if row.final_label.strip()]
    model = json.loads(model_path.read_text(encoding="utf-8")) if model_path.exists() else {}

    evaluated_count = len(rows)
    heuristic_or_trained = str(model.get("heuristic_or_trained", "heuristic_baseline"))
    preset_scores = model.get("preset_scores", {}) if isinstance(model.get("preset_scores", {}), dict) else {}
    matches = 0
    for row in rows:
        predicted = float(preset_scores.get(row.preset_id, row.user_rating / 10.0 if row.user_rating else 0.5))
        keep_like = row.final_label.lower() in {"keep", "good", "reuse"}
        predicted_keep = predicted >= 0.5
        if keep_like == predicted_keep:
            matches += 1
    accuracy = (matches / evaluated_count) if evaluated_count else 0.0

    report_path = ROOT_DIR / "reports" / "model_training" / "chordpotion_preset_selector_eval_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(
            [
                "# ChordPotion Preset Selector Evaluation Report",
                "",
                f"- heuristic_or_trained: `{heuristic_or_trained}`",
                f"- evaluated_examples: `{evaluated_count}`",
                f"- proxy_accuracy: `{accuracy:.3f}`",
                "- note: `evaluation uses local labeled audition outcomes only`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"EVALUATED_EXAMPLES={evaluated_count}")
    print(f"HEURISTIC_OR_TRAINED={heuristic_or_trained}")
    print(f"PROXY_ACCURACY={accuracy:.3f}")
    print(f"EVAL_REPORT={report_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
