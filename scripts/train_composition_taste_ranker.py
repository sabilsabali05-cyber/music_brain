from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.taste_learning.composition_ranker import result_to_dict, train_ranker  # noqa: E402


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def main() -> int:
    feedback_path = ROOT_DIR / "datasets" / "taste_learning" / "taste_feedback.jsonl"
    model_path = ROOT_DIR / "artifacts" / "taste_learning" / "composition_ranker" / "model.json"
    report_json = ROOT_DIR / "reports" / "taste_learning" / "composition_ranker_training_report.json"
    report_md = ROOT_DIR / "reports" / "taste_learning" / "composition_ranker_training_report.md"
    result = train_ranker(feedback_path, model_path)
    payload = result_to_dict(result)
    payload["model_path"] = _repo_rel(Path(payload["model_path"]))
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# Composition Taste Ranker Training Report",
                "",
                f"- training_examples_count: `{payload['training_examples_count']}`",
                f"- authorized_examples_count: `{payload['authorized_examples_count']}`",
                f"- blocked_examples_count: `{payload['blocked_examples_count']}`",
                f"- trained_ranker_used: `{str(payload['trained_ranker_used']).lower()}`",
                f"- heuristic_ranker_used: `{str(payload['heuristic_ranker_used']).lower()}`",
                f"- train_status: `{payload['train_status']}`",
                f"- model_path: `{payload['model_path']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"TRAINING_REPORT_JSON={report_json.as_posix()}")
    print(f"TRAINING_REPORT_MD={report_md.as_posix()}")
    print(f"TRAINING_EXAMPLES_COUNT={payload['training_examples_count']}")
    print(f"TRAINED_RANKER_USED={str(payload['trained_ranker_used']).lower()}")
    print(f"HEURISTIC_RANKER_USED={str(payload['heuristic_ranker_used']).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
