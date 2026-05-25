from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.training_corpus.canonical_music_corpus_schema import (
    CANONICAL_FIELDS,
    LABEL_FIELDS,
    NormalizationStats,
    normalize_music_corpus_row,
)
INVENTORY_JSON = ROOT_DIR / "reports" / "database" / "database_artifact_inventory.json"
INVENTORY_MD = ROOT_DIR / "reports" / "database" / "database_artifact_inventory.md"
NORMALIZED_JSONL = ROOT_DIR / "datasets" / "normalized_music_corpus" / "normalized_music_corpus.jsonl"
NORMALIZED_REPORT_JSON = ROOT_DIR / "reports" / "database" / "normalized_music_corpus_report.json"
NORMALIZED_REPORT_MD = ROOT_DIR / "reports" / "database" / "normalized_music_corpus_report.md"

DATE_MIN = date(2026, 5, 21)
DATE_MAX = date(2026, 5, 24)

ARTIFACT_GLOBS = [
    "datasets/training_exports/**/*.json",
    "datasets/training_exports/**/*.jsonl",
    "datasets/review_queue/**/*.json",
    "datasets/review_queue/**/*.jsonl",
    "datasets/model_training/**/*.jsonl",
    "datasets/feedback/**/*.json",
    "datasets/feedback/**/*.jsonl",
    "reports/review_queue/**/*.json",
    "reports/controlled_ingestion/**/*.json",
    "reports/batches/**/*trusted_export_report.json",
    "reports/mass_ingestion/**/*.json",
    "reports/data_quality/**/*.json",
    "reports/dataset_quality/**/*.json",
    "reports/model_training/**/*.json",
    "reports/privacy/**/*.json",
    "outputs/**/*review*.json",
]


def _resolve_output_paths(root: Path) -> dict[str, Path]:
    return {
        "inventory_json": root / "reports" / "database" / "database_artifact_inventory.json",
        "inventory_md": root / "reports" / "database" / "database_artifact_inventory.md",
        "normalized_jsonl": root / "datasets" / "normalized_music_corpus" / "normalized_music_corpus.jsonl",
        "report_json": root / "reports" / "database" / "normalized_music_corpus_report.json",
        "report_md": root / "reports" / "database" / "normalized_music_corpus_report.md",
    }


@dataclass(frozen=True)
class ParsedArtifact:
    path: Path
    rows: list[dict[str, Any]]
    file_type: str


def _safe_int(value: Any) -> int:
    try:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value.strip():
            return int(float(value.strip()))
    except ValueError:
        return 0
    return 0


def _parse_iso_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _extract_rows_from_json_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ("rows", "records", "items", "new_public_leaks", "pre_existing_historical_path_debt"):
        value = payload.get(key)
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            return [item for item in value if isinstance(item, dict)]
    return [payload]


def _parse_artifact(path: Path) -> ParsedArtifact | None:
    suffix = path.suffix.lower()
    if suffix not in {".json", ".jsonl"}:
        return None
    if suffix == ".jsonl":
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                rows.append(parsed)
        return ParsedArtifact(path=path, rows=rows, file_type="jsonl")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ParsedArtifact(path=path, rows=[], file_type="json")
    return ParsedArtifact(path=path, rows=_extract_rows_from_json_payload(payload), file_type="json")


def _collect_candidate_paths(root: Path) -> list[Path]:
    unique: set[Path] = set()
    for pattern in ARTIFACT_GLOBS:
        for path in root.glob(pattern):
            if path.is_file():
                unique.add(path.resolve())
    return sorted(unique)


def _artifact_in_scope(path: Path, rows: list[dict[str, Any]]) -> bool:
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).date()
    if DATE_MIN <= modified <= DATE_MAX:
        return True
    for row in rows[:50]:
        for key in ("created_at", "timestamp", "generated_at"):
            parsed = _parse_iso_date(row.get(key))
            if parsed and DATE_MIN <= parsed <= DATE_MAX:
                return True
    path_text = path.as_posix()
    if any(token in path_text for token in ("datasets/review_queue", "datasets/training_exports", "datasets/feedback")):
        return True
    return any(token in path_text for token in ("20260521", "20260522", "20260523", "20260524"))


def _count_by_status(rows: list[dict[str, Any]]) -> dict[str, int]:
    accepted = 0
    review_required = 0
    rejected = 0
    training_allowed = 0
    production_only = 0
    retrieval_only = 0
    missing_policy = 0
    missing_labels = 0
    schema_fields: set[str] = set()
    min_date: date | None = None
    max_date: date | None = None
    for row in rows:
        normalized, stats = normalize_music_corpus_row(
            row,
            source_artifact="inventory_scan",
        )
        schema_fields.update(row.keys())
        if normalized["review_status"] == "accepted":
            accepted += 1
        elif normalized["review_status"] == "rejected":
            rejected += 1
        else:
            review_required += 1
        if bool(normalized["training_allowed"]):
            training_allowed += 1
        if bool(normalized["production_use_allowed"]):
            production_only += 1
        if bool(normalized["retrieval_allowed"]) and not bool(normalized["training_allowed"]):
            retrieval_only += 1
        if stats.missing_policy_fields:
            missing_policy += 1
        if stats.missing_label_fields:
            missing_labels += 1
        for key in ("created_at", "normalized_at"):
            parsed = _parse_iso_date(normalized.get(key))
            if parsed is None:
                continue
            min_date = parsed if min_date is None else min(min_date, parsed)
            max_date = parsed if max_date is None else max(max_date, parsed)
    date_range = ""
    if min_date and max_date:
        date_range = f"{min_date.isoformat()}..{max_date.isoformat()}"
    elif min_date:
        date_range = min_date.isoformat()
    return {
        "accepted_count": accepted,
        "review_required_count": review_required,
        "rejected_count": rejected,
        "training_allowed_count": training_allowed,
        "production_only_count": production_only,
        "retrieval_only_count": retrieval_only,
        "missing_policy_fields_count": missing_policy,
        "missing_label_fields_count": missing_labels,
        "schema_fields": sorted(schema_fields),
        "date_range": date_range,
    }


def build_database_inventory(root: Path = ROOT_DIR) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for path in _collect_candidate_paths(root):
        parsed = _parse_artifact(path)
        if parsed is None:
            continue
        if not _artifact_in_scope(path, parsed.rows):
            continue
        status_counts = _count_by_status(parsed.rows)
        artifacts.append(
            {
                "path": path.relative_to(root).as_posix(),
                "file_type": parsed.file_type,
                "row_count": len(parsed.rows),
                "schema_fields": status_counts["schema_fields"],
                "date_range": status_counts["date_range"],
                "accepted_count": status_counts["accepted_count"],
                "review_required_count": status_counts["review_required_count"],
                "rejected_count": status_counts["rejected_count"],
                "training_allowed_count": status_counts["training_allowed_count"],
                "production_only_count": status_counts["production_only_count"],
                "retrieval_only_count": status_counts["retrieval_only_count"],
                "missing_policy_fields_count": status_counts["missing_policy_fields_count"],
                "missing_label_fields_count": status_counts["missing_label_fields_count"],
            }
        )
    artifacts.sort(key=lambda item: item["path"])
    return artifacts


def _write_inventory(artifacts: list[dict[str, Any]], *, inventory_json: Path, inventory_md: Path) -> None:
    inventory_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {"generated_at": datetime.now(UTC).isoformat(), "artifact_count": len(artifacts), "artifacts": artifacts}
    inventory_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Database Artifact Inventory",
        "",
        f"- artifact_count: `{len(artifacts)}`",
        "",
    ]
    for artifact in artifacts:
        lines.extend(
            [
                f"## `{artifact['path']}`",
                f"- file_type: `{artifact['file_type']}`",
                f"- row_count: `{artifact['row_count']}`",
                f"- schema_fields: `{', '.join(artifact['schema_fields'])}`",
                f"- date_range: `{artifact['date_range']}`",
                f"- accepted_count: `{artifact['accepted_count']}`",
                f"- review_required_count: `{artifact['review_required_count']}`",
                f"- rejected_count: `{artifact['rejected_count']}`",
                f"- training_allowed_count: `{artifact['training_allowed_count']}`",
                f"- production_only_count: `{artifact['production_only_count']}`",
                f"- retrieval_only_count: `{artifact['retrieval_only_count']}`",
                f"- missing_policy_fields_count: `{artifact['missing_policy_fields_count']}`",
                f"- missing_label_fields_count: `{artifact['missing_label_fields_count']}`",
                "",
            ]
        )
    inventory_md.write_text("\n".join(lines), encoding="utf-8")


def normalize_music_corpus_artifacts(root: Path = ROOT_DIR) -> dict[str, Any]:
    output_paths = _resolve_output_paths(root)
    artifacts = build_database_inventory(root)
    _write_inventory(
        artifacts,
        inventory_json=output_paths["inventory_json"],
        inventory_md=output_paths["inventory_md"],
    )

    seen_ids: set[str] = set()
    normalized_rows: list[dict[str, Any]] = []
    duplicate_rows = 0
    schema_drift_resolved_count = 0
    policy_missing_rows = 0
    label_missing_rows = 0
    accepted_rows = 0
    review_required_rows = 0
    rejected_rows = 0
    retrieval_only_rows = 0
    training_eligible_rows = 0
    validation_eligible_rows = 0
    training_candidates: list[str] = []

    for artifact in artifacts:
        parsed = _parse_artifact(root / artifact["path"])
        if parsed is None:
            continue
        source_type = "training_export" if "training_exports" in artifact["path"] else None
        for row in parsed.rows:
            canonical, stats = normalize_music_corpus_row(
                row,
                source_artifact=artifact["path"],
                source_type=source_type,
            )
            item_id = canonical["item_id"]
            if item_id in seen_ids:
                duplicate_rows += 1
                continue
            seen_ids.add(item_id)
            if stats.schema_drift_resolved:
                schema_drift_resolved_count += 1
            if stats.missing_policy_fields:
                policy_missing_rows += 1
            if stats.missing_label_fields:
                label_missing_rows += 1

            if canonical["review_status"] == "accepted":
                accepted_rows += 1
            elif canonical["review_status"] == "rejected":
                rejected_rows += 1
            else:
                review_required_rows += 1

            if canonical["retrieval_allowed"] and not canonical["training_allowed"]:
                retrieval_only_rows += 1

            policy_ok = canonical["policy_status"] == "complete"
            labels_present = not stats.missing_label_fields
            eligible = (
                canonical["review_status"] == "accepted"
                and canonical["training_allowed"] is True
                and policy_ok
                and labels_present
            )
            if eligible:
                training_candidates.append(item_id)
                training_eligible_rows += 1
            normalized_rows.append(canonical)

    for item_id in training_candidates:
        bucket = int(item_id.encode("utf-8").hex(), 16) % 10
        if bucket in {0, 1}:
            validation_eligible_rows += 1

    output_paths["normalized_jsonl"].parent.mkdir(parents=True, exist_ok=True)
    with output_paths["normalized_jsonl"].open("w", encoding="utf-8") as handle:
        for row in normalized_rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    summary = {
        "total_rows": len(normalized_rows),
        "accepted_rows": accepted_rows,
        "review_required_rows": review_required_rows,
        "rejected_rows": rejected_rows,
        "training_eligible_rows": training_eligible_rows,
        "validation_eligible_rows": validation_eligible_rows,
        "retrieval_only_rows": retrieval_only_rows,
        "policy_missing_rows": policy_missing_rows,
        "label_missing_rows": label_missing_rows,
        "duplicate_rows": duplicate_rows,
        "schema_drift_resolved_count": schema_drift_resolved_count,
        "canonical_fields": CANONICAL_FIELDS,
        "label_fields": LABEL_FIELDS,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    output_paths["report_json"].parent.mkdir(parents=True, exist_ok=True)
    output_paths["report_json"].write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Normalized Music Corpus Report",
        "",
        f"- total rows: `{summary['total_rows']}`",
        f"- accepted rows: `{summary['accepted_rows']}`",
        f"- review-required rows: `{summary['review_required_rows']}`",
        f"- rejected rows: `{summary['rejected_rows']}`",
        f"- training-eligible rows: `{summary['training_eligible_rows']}`",
        f"- validation-eligible rows: `{summary['validation_eligible_rows']}`",
        f"- retrieval-only rows: `{summary['retrieval_only_rows']}`",
        f"- policy-missing rows: `{summary['policy_missing_rows']}`",
        f"- label-missing rows: `{summary['label_missing_rows']}`",
        f"- duplicate rows: `{summary['duplicate_rows']}`",
        f"- schema drift resolved count: `{summary['schema_drift_resolved_count']}`",
        "",
        "## Notes",
        "- Missing policy fields default training_allowed to false.",
        "- Missing authorization_status and review_status default to review_required.",
        "- Splice/production-only entries are retrieval-only unless explicitly overridden.",
        "- Generated MIDI rows remain non-training unless explicitly reviewed and allowed.",
    ]
    output_paths["report_md"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize DB-like artifacts into canonical music corpus rows.")
    parser.add_argument("--root", default=str(ROOT_DIR), help="Project root path")
    args = parser.parse_args()
    root = Path(args.root)
    output_paths = _resolve_output_paths(root)
    summary = normalize_music_corpus_artifacts(root)
    print(f"NORMALIZED_CORPUS_PATH={output_paths['normalized_jsonl'].as_posix()}")
    print(f"NORMALIZED_REPORT_JSON={output_paths['report_json'].as_posix()}")
    print(f"NORMALIZED_REPORT_MD={output_paths['report_md'].as_posix()}")
    print(f"NORMALIZED_TOTAL_ROWS={summary['total_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

