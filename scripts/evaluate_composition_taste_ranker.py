from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.taste_learning.composition_ranker import LABEL_TO_TARGET, extract_features, load_model, predict_with_model, score_with_heuristic  # noqa: E402


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def main() -> int:
    feedback_path = ROOT_DIR / "datasets" / "taste_learning" / "taste_feedback.jsonl"
    model_path = ROOT_DIR / "artifacts" / "taste_learning" / "composition_ranker" / "model.json"
    report_json = ROOT_DIR / "reports" / "taste_learning" / "composition_ranker_eval_report.json"
    report_md = ROOT_DIR / "reports" / "taste_learning" / "composition_ranker_eval_report.md"
    rows = _read_jsonl(feedback_path)
    authorized = [
        row
        for row in rows
        if str(row.get("authorization_status", "")).strip().lower() in {"authorized", "public_domain", "self_owned"}
        and bool(row.get("source_authorized_for_learning", False))
        and str(row.get("taste_label", "")).strip().lower() in LABEL_TO_TARGET
    ]
    model = load_model(model_path)
    trained = model.get("model_type") == "tiny_linear_preference_ranker"
    errors: list[float] = []
    for row in authorized:
        features = extract_features(row)
        pred = predict_with_model(features, model) if trained else score_with_heuristic(features)
        target = LABEL_TO_TARGET[str(row.get("taste_label", "")).strip().lower()]
        errors.append(abs(pred - target))
    mae = sum(errors) / len(errors) if errors else 0.0
    payload = {
        "evaluation_examples_count": len(authorized),
        "trained_ranker_used": trained,
        "heuristic_ranker_used": not trained,
        "mae": round(mae, 6),
        "status": "ok" if authorized else "no_authorized_feedback_examples",
        "policy": {
            "authorized_data_only": True,
            "no_cloud_calls": True,
        },
    }
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# Composition Taste Ranker Evaluation Report",
                "",
                f"- evaluation_examples_count: `{payload['evaluation_examples_count']}`",
                f"- trained_ranker_used: `{str(payload['trained_ranker_used']).lower()}`",
                f"- heuristic_ranker_used: `{str(payload['heuristic_ranker_used']).lower()}`",
                f"- mae: `{payload['mae']}`",
                f"- status: `{payload['status']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"EVAL_REPORT_JSON={report_json.as_posix()}")
    print(f"EVAL_REPORT_MD={report_md.as_posix()}")
    print(f"EVAL_EXAMPLES_COUNT={payload['evaluation_examples_count']}")
    print(f"TRAINED_RANKER_USED={str(payload['trained_ranker_used']).lower()}")
    print(f"HEURISTIC_RANKER_USED={str(payload['heuristic_ranker_used']).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
