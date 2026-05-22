from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _decision_from_manifest(manifest: dict[str, Any]) -> str:
    feature_pack = manifest.get("source_feature_pack_path")
    if not isinstance(feature_pack, str) or not feature_pack.strip():
        return "unknown"
    audit_path = Path(feature_pack) / "trust" / "training_data_audit.json"
    if not audit_path.exists():
        return "unknown"
    audit_payload = _read_json(audit_path)
    return str(audit_payload.get("dataset_inclusion_decision", "unknown"))


def summarize_training_exports(exports_root: Path) -> tuple[Path, Path]:
    manifests = sorted(exports_root.glob("**/export_manifest.json"))
    totals = {
        "total_performances": 0,
        "total_source_ai_records": 0,
        "total_accepted_observation_records": 0,
        "total_weak_label_records": 0,
        "total_audio_midi_only_records": 0,
        "total_review_required_records": 0,
        "total_quarantined_records": 0,
    }
    limitations_counter: Counter[str] = Counter()
    decision_counter: Counter[str] = Counter()
    zero_accepted: list[str] = []
    has_quarantine: list[str] = []

    for manifest_path in manifests:
        manifest = _read_json(manifest_path)
        if not manifest:
            continue
        performance_id = str(manifest.get("performance_id", manifest_path.parent.parent.name))
        totals["total_performances"] += 1
        totals["total_source_ai_records"] += int(manifest.get("source_ai_record_count", 0) or 0)
        accepted = int(manifest.get("accepted_observation_count", 0) or 0)
        weak = int(manifest.get("weak_label_count", 0) or 0)
        audio_only = int(manifest.get("audio_midi_only_count", 0) or 0)
        review = int(manifest.get("review_required_count", 0) or 0)
        quarantined = int(manifest.get("quarantined_count", 0) or 0)
        totals["total_accepted_observation_records"] += accepted
        totals["total_weak_label_records"] += weak
        totals["total_audio_midi_only_records"] += audio_only
        totals["total_review_required_records"] += review
        totals["total_quarantined_records"] += quarantined
        if accepted == 0:
            zero_accepted.append(performance_id)
        if quarantined > 0:
            has_quarantine.append(performance_id)
        for item in manifest.get("limitations", []):
            if isinstance(item, str) and item.strip():
                limitations_counter[item.strip()] += 1
        for item in manifest.get("warnings", []):
            if isinstance(item, str) and item.strip():
                limitations_counter[item.strip()] += 1
        decision_counter[_decision_from_manifest(manifest)] += 1

    source_total = max(1, totals["total_source_ai_records"])
    accepted_pct = round((totals["total_accepted_observation_records"] / source_total) * 100.0, 4)
    review_pct = round((totals["total_review_required_records"] / source_total) * 100.0, 4)
    summary_payload = {
        **totals,
        "accepted_percentage": accepted_pct,
        "review_required_percentage": review_pct,
        "performances_by_dataset_inclusion_decision": dict(sorted(decision_counter.items())),
        "performances_with_zero_accepted_records": sorted(zero_accepted),
        "performances_with_quarantined_records": sorted(has_quarantine),
        "top_limitations_or_warnings": [{"message": text, "count": count} for text, count in limitations_counter.most_common(10)],
    }

    json_path = exports_root / "training_exports_summary.json"
    md_path = exports_root / "training_exports_summary.md"
    json_path.write_text(json.dumps(summary_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Training Exports Summary",
        "",
        f"- total performances: `{summary_payload['total_performances']}`",
        f"- total source AI records: `{summary_payload['total_source_ai_records']}`",
        f"- total accepted observation records: `{summary_payload['total_accepted_observation_records']}`",
        f"- total weak label records: `{summary_payload['total_weak_label_records']}`",
        f"- total audio_midi_only records: `{summary_payload['total_audio_midi_only_records']}`",
        f"- total review_required records: `{summary_payload['total_review_required_records']}`",
        f"- total quarantined records: `{summary_payload['total_quarantined_records']}`",
        f"- accepted percentage: `{summary_payload['accepted_percentage']}`",
        f"- review_required percentage: `{summary_payload['review_required_percentage']}`",
        "",
        "## Performances by dataset inclusion decision",
    ]
    if summary_payload["performances_by_dataset_inclusion_decision"]:
        for key, value in summary_payload["performances_by_dataset_inclusion_decision"].items():
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Performances with zero accepted records"])
    if zero_accepted:
        lines.extend(f"- {item}" for item in sorted(zero_accepted))
    else:
        lines.append("- none")
    lines.extend(["", "## Performances with quarantined records"])
    if has_quarantine:
        lines.extend(f"- {item}" for item in sorted(has_quarantine))
    else:
        lines.append("- none")
    lines.extend(["", "## Top limitations/warnings"])
    if summary_payload["top_limitations_or_warnings"]:
        for item in summary_payload["top_limitations_or_warnings"]:
            lines.append(f"- {item['message']} (`{item['count']}`)")
    else:
        lines.append("- none")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path.resolve(), md_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize all training export manifests under a root folder.")
    parser.add_argument("exports_root", nargs="?", default="datasets/training_exports", help="Root folder containing training export folders")
    args = parser.parse_args()
    json_path, md_path = summarize_training_exports(Path(args.exports_root))
    print(f"TRAINING_EXPORTS_SUMMARY_JSON={json_path.as_posix()}")
    print(f"TRAINING_EXPORTS_SUMMARY_MD={md_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
