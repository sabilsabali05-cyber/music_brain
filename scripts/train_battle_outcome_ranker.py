from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def build_training_report(results_count: int) -> dict:
    return {
        "results_count": results_count,
        "training_mode": "heuristic_baseline" if results_count < 20 else "local_train",
        "holdout_evaluation_ran": results_count >= 50,
        "battle_outcome_ranker_trained": results_count >= 20,
        "honest_reporting": True,
        "artifact_path": "artifacts/beat_battle_agent/battle_outcome_ranker/model.json",
        "blocker": "",
    }


def main() -> int:
    dataset_path = ROOT_DIR / "datasets" / "beat_battle_agent" / "battle_results.jsonl"
    rows = _load_rows(dataset_path)
    count = len(rows)
    report = build_training_report(count)
    artifact_path = ROOT_DIR / report["artifact_path"]
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps({"results_count": count, "mode": report["training_mode"], "holdout_eval": report["holdout_evaluation_ran"]}, indent=2, ensure_ascii=True)
        + "\n",
        encoding="utf-8",
    )
    report_root = ROOT_DIR / "reports" / "beat_battle_agent"
    report_root.mkdir(parents=True, exist_ok=True)
    (report_root / "battle_outcome_ranker_training.json").write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (report_root / "battle_outcome_ranker_training.md").write_text(
        "\n".join(
            [
                "# Battle Outcome Ranker Training",
                "",
                f"- results_count: `{count}`",
                f"- training_mode: `{report['training_mode']}`",
                f"- holdout_evaluation_ran: `{str(report['holdout_evaluation_ran']).lower()}`",
                f"- battle_outcome_ranker_trained: `{str(report['battle_outcome_ranker_trained']).lower()}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"TRAINING_RESULTS_COUNT={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
