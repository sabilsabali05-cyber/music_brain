from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.source_audio_study import SourceAudioStudyItem

TRUST_GLOB = "features/performances/*/*/trust/training_data_audit.json"
OUT_DIR = ROOT_DIR / "datasets" / "source_audio_study"
OUT_JSONL = OUT_DIR / "source_audio_study_manifest.jsonl"
REPORT_DIR = ROOT_DIR / "reports" / "source_audio_study"
REPORT_JSON = REPORT_DIR / "source_audio_study_manifest_report.json"
REPORT_MD = REPORT_DIR / "source_audio_study_manifest_report.md"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


def _build_item(path: Path, payload: dict[str, Any]) -> SourceAudioStudyItem:
    artifacts = payload.get("artifacts", {}) if isinstance(payload.get("artifacts"), dict) else {}
    source_ref = str(artifacts.get("source_audio_reference", "<PRIVATE_LOCAL_PATH>/unknown"))
    perf_id = str(payload.get("performance_id", path.parents[2].name))
    auth = str(payload.get("authorization_status", "unknown")).strip().lower() or "unknown"
    retrieval_allowed = _bool(payload.get("retrieval_allowed"), default=True)
    training_allowed = _bool(payload.get("training_allowed"), default=False)
    analysis_allowed = _bool(payload.get("analysis_allowed"), default=False)
    try:
        trust_rel = path.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        trust_rel = path.as_posix()
    return SourceAudioStudyItem(
        item_id=f"source_audio_{perf_id}",
        source_audio_ref=source_ref,
        source_audio_ref_redacted=source_ref,
        authorization_status=auth,
        retrieval_allowed=retrieval_allowed,
        training_allowed=training_allowed,
        analysis_allowed=analysis_allowed,
        policy_separation={
            "authorization_scope": auth,
            "analysis_allowed": analysis_allowed,
            "training_allowed": training_allowed,
            "retrieval_allowed": retrieval_allowed,
            "must_not_train_on_audio": not training_allowed,
            "must_not_analyze_raw_audio_without_permission": not analysis_allowed,
        },
        provenance={
            "trust_audit_path": trust_rel,
            "generated_at": datetime.now(UTC).isoformat(),
        },
    )


def build_manifest() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(ROOT_DIR.glob(TRUST_GLOB)):
        payload = _read_json(path)
        if not payload:
            continue
        item = _build_item(path, payload)
        items.append(item.to_dict())
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "manifest_path": OUT_JSONL.relative_to(ROOT_DIR).as_posix(),
        "source_items_considered": len(items),
        "analysis_allowed_count": sum(1 for row in items if row.get("analysis_allowed")),
        "analysis_blocked_count": sum(1 for row in items if not row.get("analysis_allowed")),
        "training_allowed_count": sum(1 for row in items if row.get("training_allowed")),
        "authorization_status_counts": {
            key: sum(1 for row in items if row.get("authorization_status") == key) for key in sorted({str(row.get("authorization_status")) for row in items})
        },
        "policy_notes": [
            "No source audio files were moved, modified, or deleted.",
            "Manifest rows separate retrieval/training/analysis authorization decisions.",
            "Raw audio analysis is blocked unless analysis_allowed=true per row.",
        ],
    }
    return items, report


def write_outputs(items: list[dict[str, Any]], report: dict[str, Any]) -> tuple[Path, Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("w", encoding="utf-8") as handle:
        for row in items:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Source Audio Study Manifest Report",
        "",
        f"- source_items_considered: `{report['source_items_considered']}`",
        f"- analysis_allowed_count: `{report['analysis_allowed_count']}`",
        f"- analysis_blocked_count: `{report['analysis_blocked_count']}`",
        f"- training_allowed_count: `{report['training_allowed_count']}`",
        "",
        "## Policy notes",
        *[f"- {line}" for line in report["policy_notes"]],
    ]
    REPORT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return OUT_JSONL, REPORT_JSON, REPORT_MD


def main() -> int:
    items, report = build_manifest()
    manifest_path, json_path, md_path = write_outputs(items, report)
    print(f"SOURCE_AUDIO_STUDY_MANIFEST={manifest_path.as_posix()}")
    print(f"SOURCE_AUDIO_STUDY_REPORT_JSON={json_path.as_posix()}")
    print(f"SOURCE_AUDIO_STUDY_REPORT_MD={md_path.as_posix()}")
    print(f"SOURCE_ITEMS_CONSIDERED={report['source_items_considered']}")
    print(f"SOURCE_ITEMS_ANALYSIS_ALLOWED={report['analysis_allowed_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
