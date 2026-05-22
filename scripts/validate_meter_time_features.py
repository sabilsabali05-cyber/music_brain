from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.trust_common import resolve_performance_context


def _safe_float(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


def _check_confidence_and_ambiguity(
    item: dict[str, Any],
    *,
    item_name: str,
    errors: list[str],
) -> None:
    conf = _safe_float(item.get("confidence"), -1.0)
    amb = _safe_float(item.get("ambiguity"), -1.0)
    if conf < 0.0 or conf > 1.0:
        errors.append(f"{item_name} has confidence outside [0,1]")
    if amb < 0.0 or amb > 1.0:
        errors.append(f"{item_name} has ambiguity outside [0,1]")


def validate_meter_time_features(performance_manifest_path: Path) -> dict[str, Any]:
    ctx = resolve_performance_context(performance_manifest_path)
    meter_time_dir = ctx["feature_dir"] / "rhythm_time"
    json_path = meter_time_dir / "meter_time_features.json"
    md_path = meter_time_dir / "meter_time_summary.md"
    errors: list[str] = []
    warnings: list[str] = []
    if not json_path.exists():
        return {
            "status": "failed",
            "errors": [f"missing meter_time features json: {json_path.as_posix()}"],
            "warnings": [],
            "meter_time_features_path": json_path.as_posix(),
        }
    if not md_path.exists():
        errors.append("missing meter_time_summary.md")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        errors.append("meter_time_features.json must be a JSON object")
        return {
            "status": "failed",
            "errors": errors,
            "warnings": warnings,
            "meter_time_features_path": json_path.as_posix(),
        }

    for field in ["summary", "microtiming_records", "subdivision_grid_records", "beat_meter_hypotheses", "cycle_pattern_records", "phrase_rhythm_records", "macro_time_records", "limitations"]:
        if field not in payload:
            errors.append(f"missing top-level field: {field}")

    for field in ["confidence", "ambiguity"]:
        value = _safe_float(payload.get(field), -1.0)
        if value < 0 or value > 1:
            errors.append(f"top-level {field} must be in [0,1]")

    limitations = payload.get("limitations", [])
    if not isinstance(limitations, list) or not limitations:
        errors.append("limitations must be a non-empty list")

    micro_records = payload.get("microtiming_records", [])
    if not isinstance(micro_records, list) or not micro_records:
        errors.append("microtiming_records must be a non-empty list")
    else:
        for idx, item in enumerate(micro_records):
            if not isinstance(item, dict):
                errors.append(f"microtiming_records[{idx}] is not an object")
                continue
            _check_confidence_and_ambiguity(item, item_name=f"microtiming_records[{idx}]", errors=errors)
            if _safe_float(item.get("local_tempo_bpm"), -1.0) < 0.0:
                errors.append(f"microtiming_records[{idx}] has negative local_tempo_bpm")
            if _safe_float(item.get("pulse_stability"), -1.0) < 0.0 or _safe_float(item.get("pulse_stability"), -1.0) > 1.0:
                errors.append(f"microtiming_records[{idx}] pulse_stability outside [0,1]")

    grid_records = payload.get("subdivision_grid_records", [])
    if not isinstance(grid_records, list) or not grid_records:
        errors.append("subdivision_grid_records must be a non-empty list")
    else:
        for idx, item in enumerate(grid_records):
            if not isinstance(item, dict):
                errors.append(f"subdivision_grid_records[{idx}] is not an object")
                continue
            _check_confidence_and_ambiguity(item, item_name=f"subdivision_grid_records[{idx}]", errors=errors)
            if _safe_float(item.get("grid_confidence"), -1.0) < 0.0 or _safe_float(item.get("grid_confidence"), -1.0) > 1.0:
                errors.append(f"subdivision_grid_records[{idx}] grid_confidence outside [0,1]")
            if str(item.get("subdivision_type", "")).strip() == "":
                errors.append(f"subdivision_grid_records[{idx}] missing subdivision_type")

    hypotheses = payload.get("beat_meter_hypotheses", [])
    if not isinstance(hypotheses, list) or not hypotheses:
        errors.append("beat_meter_hypotheses must be a non-empty list")
    else:
        if len(hypotheses) < 2:
            warnings.append("only one meter hypothesis present; ambiguity handling may be weak")
        previous_conf = 1.1
        for idx, item in enumerate(hypotheses):
            if not isinstance(item, dict):
                errors.append(f"beat_meter_hypotheses[{idx}] is not an object")
                continue
            _check_confidence_and_ambiguity(item, item_name=f"beat_meter_hypotheses[{idx}]", errors=errors)
            conf = _safe_float(item.get("confidence"), 0.0)
            if conf > previous_conf + 1e-6:
                errors.append("beat_meter_hypotheses must be sorted by descending confidence")
            previous_conf = conf
            meter = str(item.get("meter", ""))
            if meter not in {"undetermined", ""} and conf < 0.35:
                errors.append("hard meter label present with low confidence (<0.35)")
            if meter in {"undetermined", ""} and conf > 0.6:
                warnings.append("undetermined meter has unexpectedly high confidence")

    cycle_records = payload.get("cycle_pattern_records", [])
    if not isinstance(cycle_records, list) or not cycle_records:
        errors.append("cycle_pattern_records must be a non-empty list")
    else:
        for idx, item in enumerate(cycle_records):
            if not isinstance(item, dict):
                errors.append(f"cycle_pattern_records[{idx}] is not an object")
                continue
            _check_confidence_and_ambiguity(item, item_name=f"cycle_pattern_records[{idx}]", errors=errors)
            if _safe_float(item.get("cycle_length_beats"), 0.0) < 0.0:
                errors.append(f"cycle_pattern_records[{idx}] has negative cycle_length_beats")

    macro_records = payload.get("macro_time_records", [])
    if not isinstance(macro_records, list) or not macro_records:
        errors.append("macro_time_records must be a non-empty list")
    else:
        starts = []
        ends = []
        for idx, item in enumerate(macro_records):
            if not isinstance(item, dict):
                errors.append(f"macro_time_records[{idx}] is not an object")
                continue
            _check_confidence_and_ambiguity(item, item_name=f"macro_time_records[{idx}]", errors=errors)
            start = _safe_float(item.get("start_seconds"), 0.0)
            end = _safe_float(item.get("end_seconds"), 0.0)
            if end < start:
                errors.append(f"macro_time_records[{idx}] has invalid time range")
            starts.append(start)
            ends.append(end)
            if str(item.get("macro_section_candidate", "")).strip() == "":
                errors.append(f"macro_time_records[{idx}] missing macro_section_candidate")
        if starts and starts != sorted(starts):
            errors.append("macro_time_records are not ordered by start time")
        if ends and max(ends) <= 0:
            errors.append("macro_time_records contain no positive timeline coverage")

    summary = payload.get("summary", {})
    if isinstance(summary, dict):
        if _safe_float(summary.get("local_tempo_bpm_median"), -1.0) < 0.0:
            errors.append("summary.local_tempo_bpm_median cannot be negative")
        if _safe_float(summary.get("pulse_stability_mean"), -1.0) < 0.0 or _safe_float(summary.get("pulse_stability_mean"), -1.0) > 1.0:
            errors.append("summary.pulse_stability_mean must be in [0,1]")
    else:
        errors.append("summary must be an object")

    result = {
        "status": "success" if not errors else "failed",
        "meter_time_features_path": json_path.as_posix(),
        "meter_time_summary_path": md_path.as_posix(),
        "errors": errors,
        "warnings": warnings,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate extracted hierarchical meter/time features.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    result = validate_meter_time_features(Path(args.performance_manifest))
    print("METER_TIME_VALIDATION=" + json.dumps(result, ensure_ascii=True))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
