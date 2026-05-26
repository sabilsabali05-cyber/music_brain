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

from features.model_witnesses import ModelWitnessObservation

MANIFEST_PATH = ROOT_DIR / "datasets" / "source_audio_study" / "source_audio_study_manifest.jsonl"
AUDIT_PATH = ROOT_DIR / "reports" / "model_witnesses" / "model_witness_audit.json"
OUT_DIR = ROOT_DIR / "datasets" / "model_witnesses"
OUT_JSONL = OUT_DIR / "source_audio_witness_observations.jsonl"
REPORT_DIR = ROOT_DIR / "reports" / "model_witnesses"
REPORT_JSON = REPORT_DIR / "source_audio_witness_run_report.json"
REPORT_MD = REPORT_DIR / "source_audio_witness_run_report.md"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _feature_observation(item: dict[str, Any], trust_payload: dict[str, Any]) -> ModelWitnessObservation:
    meter = trust_payload.get("meter_time_intelligence", {}) if isinstance(trust_payload.get("meter_time_intelligence"), dict) else {}
    top_meter = meter.get("top_meter_hypothesis", {}) if isinstance(meter.get("top_meter_hypothesis"), dict) else {}
    evidence_points = [
        f"meter_hint={top_meter.get('meter', 'unknown')}",
        f"meter_confidence={top_meter.get('confidence', 0.0)}",
        f"safe_observations={len((trust_payload.get('field_level_training_usability', {}) or {}).get('safe_fields_for_training', []))}",
    ]
    return ModelWitnessObservation(
        observation_id=f"{item['item_id']}__heuristic_local_features",
        item_id=str(item["item_id"]),
        witness_id="heuristic_local_features",
        witness_type="local_heuristic",
        backend_status="heuristic",
        analysis_allowed=True,
        used_real_backend=False,
        heuristic_witness_label="heuristic_local_features",
        evidence_summary="local trust-audit feature extraction (non-backend heuristic witness)",
        evidence_points=evidence_points,
        confidence=0.35,
        disagreement_tags=[],
        blockers=[],
        redacted_source_ref=str(item.get("source_audio_ref_redacted", "<PRIVATE_LOCAL_PATH>/unknown")),
        raw_payload={"top_meter_hypothesis": top_meter},
    )


def _availability_by_id(audit: dict[str, Any]) -> dict[str, bool]:
    rows = audit.get("witnesses", []) if isinstance(audit.get("witnesses"), list) else []
    out: dict[str, bool] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        out[str(row.get("witness_id", ""))] = bool(row.get("available", False))
    return out


def build_observations() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest_rows = _read_jsonl(MANIFEST_PATH)
    audit_payload = _read_json(AUDIT_PATH)
    availability = _availability_by_id(audit_payload)
    observations: list[dict[str, Any]] = []
    skipped_unauthorized = 0
    skipped_unavailable = 0
    optional_witness_attempts = 0

    for item in manifest_rows:
        analysis_allowed = bool(item.get("analysis_allowed", False))
        if not analysis_allowed:
            skipped_unauthorized += 1
            continue
        provenance = item.get("provenance", {}) if isinstance(item.get("provenance"), dict) else {}
        trust_rel = str(provenance.get("trust_audit_path", "")).strip()
        trust_payload = _read_json(ROOT_DIR / trust_rel) if trust_rel else {}
        observations.append(_feature_observation(item, trust_payload).to_dict())

        for optional_witness in (
            "transcription_witnesses",
            "source_separation_witness",
            "musicbert",
            "moonbeam",
            "midigpt",
            "text2midi",
            "texture_witness",
        ):
            optional_witness_attempts += 1
            if not availability.get(optional_witness, False):
                skipped_unavailable += 1
                observations.append(
                    ModelWitnessObservation(
                        observation_id=f"{item['item_id']}__{optional_witness}_skip",
                        item_id=str(item["item_id"]),
                        witness_id=optional_witness,
                        witness_type="optional_backend",
                        backend_status="unavailable",
                        analysis_allowed=True,
                        used_real_backend=False,
                        heuristic_witness_label="backend_unavailable_skip",
                        evidence_summary=f"{optional_witness} unavailable; no fake witness output generated",
                        evidence_points=[],
                        confidence=0.0,
                        disagreement_tags=[],
                        blockers=["backend_unavailable"],
                        redacted_source_ref=str(item.get("source_audio_ref_redacted", "<PRIVATE_LOCAL_PATH>/unknown")),
                        raw_payload={},
                    ).to_dict()
                )

    counter = Counter()
    for row in observations:
        counter["witness_observations_created"] += 1
        counter["heuristic_observations"] += 1 if row.get("heuristic_witness_label") else 0
        counter["real_backend_observations"] += 1 if row.get("used_real_backend") else 0
        if row.get("backend_status") == "unavailable":
            counter["unavailable_backend_skips"] += 1
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_items_considered": len(manifest_rows),
        "source_items_analyzed": len({row["item_id"] for row in observations if row.get("analysis_allowed")}),
        "witness_observations_created": counter["witness_observations_created"],
        "heuristic_observations": counter["heuristic_observations"],
        "real_backend_observations": counter["real_backend_observations"],
        "optional_witness_attempts": optional_witness_attempts,
        "skipped_unauthorized_count": skipped_unauthorized,
        "skipped_unavailable_backend_count": skipped_unavailable,
        "unavailable_backend_skips": counter["unavailable_backend_skips"],
        "blockers": [
            "backend_unavailable" if counter["unavailable_backend_skips"] else "",
            "analysis_not_authorized" if skipped_unauthorized else "",
        ],
        "policy": {
            "no_fake_model_availability": True,
            "no_fake_source_audio_understanding": True,
            "no_cloud_calls": True,
            "analyze_raw_audio_only_when_analysis_allowed": True,
        },
    }
    report["blockers"] = [item for item in report["blockers"] if item]
    return observations, report


def write_outputs(observations: list[dict[str, Any]], report: dict[str, Any]) -> tuple[Path, Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("w", encoding="utf-8") as handle:
        for row in observations:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Source Audio Witness Run Report",
        "",
        f"- source_items_considered: `{report['source_items_considered']}`",
        f"- source_items_analyzed: `{report['source_items_analyzed']}`",
        f"- witness_observations_created: `{report['witness_observations_created']}`",
        f"- heuristic_observations: `{report['heuristic_observations']}`",
        f"- real_backend_observations: `{report['real_backend_observations']}`",
        f"- skipped_unauthorized_count: `{report['skipped_unauthorized_count']}`",
        f"- skipped_unavailable_backend_count: `{report['skipped_unavailable_backend_count']}`",
        "",
        "## Blockers",
    ]
    if report["blockers"]:
        lines.extend([f"- {item}" for item in report["blockers"]])
    else:
        lines.append("- none")
    REPORT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return OUT_JSONL, REPORT_JSON, REPORT_MD


def main() -> int:
    observations, report = build_observations()
    out_path, json_path, md_path = write_outputs(observations, report)
    print(f"SOURCE_AUDIO_WITNESS_OBSERVATIONS={out_path.as_posix()}")
    print(f"SOURCE_AUDIO_WITNESS_RUN_REPORT_JSON={json_path.as_posix()}")
    print(f"SOURCE_AUDIO_WITNESS_RUN_REPORT_MD={md_path.as_posix()}")
    print(f"SOURCE_ITEMS_ANALYZED={report['source_items_analyzed']}")
    print(f"WITNESS_OBSERVATIONS_CREATED={report['witness_observations_created']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
