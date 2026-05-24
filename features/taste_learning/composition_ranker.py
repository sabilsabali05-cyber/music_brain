from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .taste_feedback_schema import CORE_TASTE_LABELS


LABEL_TO_TARGET = {"love": 1.0, "like": 0.8, "neutral": 0.5, "dislike": 0.2, "reject": 0.0}


@dataclass(frozen=True)
class RankerTrainingResult:
    training_examples_count: int
    authorized_examples_count: int
    blocked_examples_count: int
    trained_ranker_used: bool
    heuristic_ranker_used: bool
    train_status: str
    model_path: str


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return default


def extract_features(row: dict[str, Any]) -> dict[str, float]:
    return {
        "musicality_score": _safe_float(row.get("musicality_score"), 0.5),
        "groove_score": _safe_float(row.get("groove_score"), 0.5),
        "harmony_score": _safe_float(row.get("harmony_score"), 0.5),
        "density_score": _safe_float(row.get("density_score"), 0.5),
        "variety_score": _safe_float(row.get("variety_score"), 0.5),
        "golden_section_alignment": _safe_float(row.get("golden_section_alignment"), 0.5),
        "phrase_ratio_score": _safe_float(row.get("phrase_ratio_score"), 0.5),
        "rhythm_ratio_score": _safe_float(row.get("rhythm_ratio_score"), 0.5),
        "interval_ratio_score": _safe_float(row.get("interval_ratio_score"), 0.5),
        "density_ratio_score": _safe_float(row.get("density_ratio_score"), 0.5),
        "ratio_musicality_score": _safe_float(row.get("ratio_musicality_score"), 0.5),
    }


def score_with_heuristic(features: dict[str, float]) -> float:
    return (
        features["musicality_score"] * 0.33
        + features["groove_score"] * 0.24
        + features["harmony_score"] * 0.19
        + features["density_score"] * 0.1
        + features["variety_score"] * 0.08
        + features["ratio_musicality_score"] * 0.04
        + features["golden_section_alignment"] * 0.004
        + features["phrase_ratio_score"] * 0.004
        + features["rhythm_ratio_score"] * 0.004
        + features["interval_ratio_score"] * 0.004
        + features["density_ratio_score"] * 0.004
    )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
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


def _train_linear_regression(rows: list[dict[str, Any]]) -> dict[str, float]:
    # Tiny local model; no cloud, no heavy dependencies.
    feature_keys = list(extract_features({}).keys())
    weights = {"bias": 0.0, **{key: 0.0 for key in feature_keys}}
    lr = 0.08
    for _ in range(180):
        for row in rows:
            features = extract_features(row)
            pred = (
                weights["bias"]
                + sum(weights[name] * value for name, value in features.items())
            )
            label = str(row.get("taste_label", "")).strip().lower()
            target = LABEL_TO_TARGET.get(label, 0.5)
            err = pred - target
            weights["bias"] -= lr * err
            for name, value in features.items():
                weights[name] -= lr * err * value
    return weights


def predict_with_model(features: dict[str, float], model_payload: dict[str, Any]) -> float:
    if model_payload.get("model_type") != "tiny_linear_preference_ranker":
        return score_with_heuristic(features)
    weights = model_payload.get("weights", {})
    score = _safe_float(weights.get("bias"), 0.0)
    for key, value in features.items():
        score += _safe_float(weights.get(key), 0.0) * value
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def train_ranker(feedback_path: Path, model_path: Path) -> RankerTrainingResult:
    rows = _load_jsonl(feedback_path)
    labelable = [row for row in rows if str(row.get("taste_label", "")).strip().lower() in CORE_TASTE_LABELS]
    authorized = [
        row
        for row in labelable
        if str(row.get("authorization_status", "")).strip().lower() in {"authorized", "public_domain", "self_owned"}
        and bool(row.get("source_authorized_for_learning", False))
    ]
    blocked = len(labelable) - len(authorized)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    if len(authorized) < 20:
        payload = {
            "model_type": "heuristic_baseline",
            "trained_ranker_used": False,
            "heuristic_ranker_used": True,
            "training_examples_count": len(authorized),
            "blocked_examples_count": blocked,
        }
        model_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        return RankerTrainingResult(
            training_examples_count=len(authorized),
            authorized_examples_count=len(authorized),
            blocked_examples_count=blocked,
            trained_ranker_used=False,
            heuristic_ranker_used=True,
            train_status="heuristic_baseline_only_insufficient_rows",
            model_path=model_path.as_posix(),
        )
    weights = _train_linear_regression(authorized)
    payload = {
        "model_type": "tiny_linear_preference_ranker",
        "trained_ranker_used": True,
        "heuristic_ranker_used": False,
        "training_examples_count": len(authorized),
        "blocked_examples_count": blocked,
        "weights": weights,
    }
    model_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return RankerTrainingResult(
        training_examples_count=len(authorized),
        authorized_examples_count=len(authorized),
        blocked_examples_count=blocked,
        trained_ranker_used=True,
        heuristic_ranker_used=False,
        train_status="trained_small_local_ranker",
        model_path=model_path.as_posix(),
    )


def rank_candidates(candidate_rows: list[dict[str, Any]], model_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    payload = model_payload or {"model_type": "heuristic_baseline"}
    out: list[dict[str, Any]] = []
    for row in candidate_rows:
        features = extract_features(row)
        if payload.get("model_type") == "tiny_linear_preference_ranker":
            score = predict_with_model(features, payload)
            mode = "trained"
        else:
            score = score_with_heuristic(features)
            mode = "heuristic"
        enriched = dict(row)
        enriched["ranker_mode"] = mode
        enriched["ranker_score"] = round(score, 6)
        out.append(enriched)
    out.sort(key=lambda item: float(item.get("ranker_score", 0.0)), reverse=True)
    return out


def load_model(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"model_type": "heuristic_baseline"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"model_type": "heuristic_baseline"}
    return payload if isinstance(payload, dict) else {"model_type": "heuristic_baseline"}


def result_to_dict(result: RankerTrainingResult) -> dict[str, Any]:
    return asdict(result)
