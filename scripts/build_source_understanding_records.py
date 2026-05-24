from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.source_understanding import build_source_understanding_record, map_source_to_generation  # noqa: E402


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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _top(rows: list[dict[str, Any]], key: str, limit: int = 25) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: float(row.get(key, 0.0)), reverse=True)[:limit]
    return [{"record_id": row["record_id"], key: row.get(key, 0.0)} for row in ordered]


def _load_raw_audio_policy() -> bool:
    config_path = ROOT_DIR / "config" / "local_audio_processing.local.json"
    if not config_path.exists():
        return False
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return bool(payload.get("allow_raw_audio_processing", False))


def main() -> int:
    normalized_rows = _read_jsonl(ROOT_DIR / "datasets" / "normalized_music_corpus" / "normalized_music_corpus.jsonl")
    intelligence_rows = _read_jsonl(ROOT_DIR / "datasets" / "music_intelligence" / "music_intelligence_records.jsonl")
    theory_rows = _read_jsonl(ROOT_DIR / "datasets" / "music_theory" / "theory_understanding_records.jsonl")
    feedback_rows = _read_jsonl(ROOT_DIR / "datasets" / "feedback" / "generation_feedback.jsonl")

    evidence_by_id = {str(row.get("item_id", "")): row for row in intelligence_rows}
    theory_by_id = {str(row.get("item_id", "")): row for row in theory_rows}
    feedback_by_id = {str(row.get("item_id", "")): row for row in feedback_rows}
    allow_raw_audio = _load_raw_audio_policy()

    records: list[dict[str, Any]] = []
    blocked_policy = 0
    blocked_conf = 0
    evidence_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()

    for row in normalized_rows:
        item_id = str(row.get("item_id", "")).strip()
        if not item_id:
            continue
        intelligence = evidence_by_id.get(item_id, {})
        theory = theory_by_id.get(item_id, {})
        feedback = feedback_by_id.get(item_id, {})
        source_type = str(row.get("source_type", "symbolic")).strip().lower() or "symbolic"
        auth = str(row.get("authorization_status", "unknown")).strip().lower()
        evidence_types = [
            "normalized_corpus_row",
            "music_intelligence_row" if intelligence else "",
            "theory_understanding_row" if theory else "",
            "feedback_row" if feedback else "",
        ]
        if source_type in {"raw_audio", "source_audio"}:
            evidence_types.append("raw_audio_source")
        confidence = float(theory.get("generation_usefulness_score", intelligence.get("scores", {}).get("generation_readiness", 0.45)))
        controls = {
            "tempo_hint_bpm": int(80 + 70 * float(theory.get("rhythm_identity_score", 0.4))),
            "density": float(theory.get("texture_value_score", 0.45)),
            "complexity": float(theory.get("harmonic_interest_score", 0.4)),
            "motif_repetition": float(theory.get("motif_reusability_score", 0.5)),
        }
        tags = []
        if controls["density"] > 0.66:
            tags.append("high_energy")
        if controls["complexity"] > 0.6:
            tags.append("harmonic_rich")
        if controls["density"] < 0.35:
            tags.append("minimal")
        if float(theory.get("random_note_penalty", 0.0)) > 0.5:
            tags.append("overbusy")
        record = build_source_understanding_record(
            record_id=f"source_understanding_{item_id}",
            item_id=item_id,
            source_artifact=str(row.get("source_artifact", "")),
            source_path_redacted=str(row.get("source_path_redacted", row.get("source_artifact", ""))),
            source_type=source_type,
            authorization_status=auth,
            training_allowed=bool(row.get("training_allowed", False)),
            retrieval_allowed=bool(row.get("retrieval_allowed", True)),
            raw_audio_processing_allowed=allow_raw_audio,
            evidence_types=evidence_types,
            evidence_summary="; ".join(sorted({item for item in evidence_types if item})),
            confidence=confidence,
            confidence_reason="fused from theory/intelligence artifacts only; no fake source-audio inference",
            generation_tags=tags,
            generation_controls=controls,
        )
        mapped = map_source_to_generation(record)
        payload = record.to_dict()
        payload["generation_controls_mapped"] = {
            "tempo_range": mapped.tempo_range,
            "rhythmic_density": mapped.rhythmic_density,
            "harmonic_complexity": mapped.harmonic_complexity,
            "motif_repetition": mapped.motif_repetition,
            "arrangement_energy_curve": mapped.arrangement_energy_curve,
            "preserve_tags": mapped.preserve_tags,
            "avoid_tags": mapped.avoid_tags,
            "confidence": mapped.confidence,
        }
        records.append(payload)
        source_counter[source_type] += 1
        for ev in payload["evidence_types"]:
            evidence_counter[ev] += 1
        if payload["blocked_by_policy"]:
            blocked_policy += 1
        if payload["blocked_by_confidence"]:
            blocked_conf += 1

    usable = [row for row in records if row.get("usable_as_generation_evidence")]
    report_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "rows_considered": len(normalized_rows),
        "records_built": len(records),
        "usable_source_evidence_count": len(usable),
        "blocked_by_policy_count": blocked_policy,
        "blocked_by_confidence_count": blocked_conf,
        "raw_audio_processing_allowed": allow_raw_audio,
        "source_type_counts": dict(source_counter),
        "evidence_type_counts": dict(evidence_counter),
        "top_25_high_confidence": _top(records, "confidence"),
        "top_25_generation_ready": _top(usable, "confidence"),
        "top_25_blocked_confidence": _top([row for row in records if row.get("blocked_by_confidence")], "confidence"),
        "top_25_blocked_policy": _top([row for row in records if row.get("blocked_by_policy")], "confidence"),
        "policy": {
            "no_cloud_calls": True,
            "no_fake_source_audio_understanding": True,
            "no_fake_model_training": True,
            "no_raw_audio_processing_without_local_authorization": True,
        },
    }

    out_jsonl = ROOT_DIR / "datasets" / "source_understanding" / "source_understanding_records.jsonl"
    report_json = ROOT_DIR / "reports" / "source_understanding" / "source_understanding_report.json"
    report_md = ROOT_DIR / "reports" / "source_understanding" / "source_understanding_report.md"
    _write_jsonl(out_jsonl, records)
    _write_json(report_json, report_payload)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(
        "\n".join(
            [
                "# Source Understanding Report",
                "",
                f"- rows_considered: `{report_payload['rows_considered']}`",
                f"- records_built: `{report_payload['records_built']}`",
                f"- usable_source_evidence_count: `{report_payload['usable_source_evidence_count']}`",
                f"- blocked_by_policy_count: `{report_payload['blocked_by_policy_count']}`",
                f"- blocked_by_confidence_count: `{report_payload['blocked_by_confidence_count']}`",
                f"- raw_audio_processing_allowed: `{str(report_payload['raw_audio_processing_allowed']).lower()}`",
                "",
                "## Top lists",
                "- top_25_high_confidence: see json",
                "- top_25_generation_ready: see json",
                "- top_25_blocked_confidence: see json",
                "- top_25_blocked_policy: see json",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"SOURCE_UNDERSTANDING_RECORDS={out_jsonl.as_posix()}")
    print(f"SOURCE_UNDERSTANDING_REPORT_JSON={report_json.as_posix()}")
    print(f"SOURCE_UNDERSTANDING_REPORT_MD={report_md.as_posix()}")
    print(f"SOURCE_UNDERSTANDING_RECORDS_COUNT={len(records)}")
    print(f"USABLE_SOURCE_EVIDENCE_COUNT={len(usable)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
