from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from features.texture_sound.sample_seed_schema import (
    SampleLibraryIndexReport,
    SampleLibraryManifest,
    SampleSeedRecord,
    build_sample_seed_record,
)

SUPPORTED_EXTENSIONS = {".wav", ".aif", ".aiff", ".flac", ".mp3", ".ogg", ".m4a"}


@dataclass(frozen=True)
class IndexResult:
    manifest_path: Path
    records_path: Path
    report_json_path: Path
    report_markdown_path: Path
    report: SampleLibraryIndexReport


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_slug(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in value).strip("_")
    return cleaned or "library"


def load_library_config(config_path: Path) -> dict[str, Any]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    required = [
        "library_id",
        "root_path",
        "source_type",
        "intended_uses",
        "authorization_status",
        "ingestion_policy",
    ]
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"Missing config keys: {', '.join(sorted(missing))}")
    if payload["source_type"] != "local_sample_seed_library":
        raise ValueError("source_type must be local_sample_seed_library for this indexer")
    if not isinstance(payload["intended_uses"], list):
        raise ValueError("intended_uses must be a list")
    if not isinstance(payload["ingestion_policy"], dict):
        raise ValueError("ingestion_policy must be an object")
    return payload


def iter_files(root_path: Path, include_nested_folders: bool) -> list[Path]:
    iterator = root_path.rglob("*") if include_nested_folders else root_path.glob("*")
    files = [path for path in iterator if path.is_file()]
    return sorted(files, key=lambda item: item.as_posix().lower())


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def probe_audio_metadata(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=codec_name,sample_rate,channels:format=duration,format_name",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return {}
    if result.returncode != 0:
        return {}
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return {}
    stream = {}
    for candidate in payload.get("streams", []):
        if isinstance(candidate, dict) and candidate.get("codec_name"):
            stream = candidate
            break
    fmt = payload.get("format", {}) if isinstance(payload.get("format"), dict) else {}
    duration: float | None = None
    try:
        raw_duration = fmt.get("duration")
        if raw_duration is not None:
            duration = float(raw_duration)
    except (TypeError, ValueError):
        duration = None
    sample_rate: int | None = None
    try:
        raw_rate = stream.get("sample_rate")
        if raw_rate is not None:
            sample_rate = int(raw_rate)
    except (TypeError, ValueError):
        sample_rate = None
    channels: int | None = None
    try:
        raw_channels = stream.get("channels")
        if raw_channels is not None:
            channels = int(raw_channels)
    except (TypeError, ValueError):
        channels = None
    format_name = fmt.get("format_name")
    if isinstance(format_name, str) and format_name:
        normalized_format = format_name.split(",")[0].strip().lower()
    else:
        normalized_format = path.suffix.lower().lstrip(".") or None
    return {
        "duration_seconds": duration,
        "sample_rate": sample_rate,
        "channels": channels,
        "format": normalized_format,
    }


def _build_report_markdown(report: SampleLibraryIndexReport) -> str:
    lines = [
        "# Sample Library Index Report",
        "",
        f"- library_id: {report['library_id']}",
        f"- source_type: {report['source_type']}",
        f"- root_path: {report['root_path']}",
        f"- generated_at: {report['generated_at']}",
        f"- files_scanned: {report['files_scanned']}",
        f"- supported_files_indexed: {report['supported_files_indexed']}",
        f"- unsupported_files_skipped: {report['unsupported_files_skipped']}",
        f"- unreadable_or_problem_files: {report['unreadable_or_problem_files']}",
        "",
        "## Notes",
    ]
    lines.extend(f"- {note}" for note in report["notes"])
    lines.append("")
    lines.append("## Unsupported Files (up to 50)")
    if report["unsupported_files"]:
        lines.extend(f"- {item}" for item in report["unsupported_files"][:50])
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Unreadable/Problem Files (up to 50)")
    if report["unreadable_files"]:
        lines.extend(f"- {item}" for item in report["unreadable_files"][:50])
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def index_sample_library(config_path: Path) -> IndexResult:
    config = load_library_config(config_path)
    library_id = str(config["library_id"])
    root_path = Path(str(config["root_path"]))
    if not root_path.exists():
        raise FileNotFoundError(f"Library root does not exist: {root_path}")
    ingestion_policy = dict(config["ingestion_policy"])
    include_nested = bool(ingestion_policy.get("include_nested_folders", True))
    hash_files = bool(ingestion_policy.get("hash_files", True))

    dataset_root = Path("datasets") / "sample_libraries" / _safe_slug(library_id)
    report_root = Path("reports") / "sample_libraries"
    dataset_root.mkdir(parents=True, exist_ok=True)
    report_root.mkdir(parents=True, exist_ok=True)

    records_path = dataset_root / "sample_seed_records.jsonl"
    manifest_path = dataset_root / "sample_library_manifest.json"
    report_json_path = report_root / f"{_safe_slug(library_id)}_index_report.json"
    report_markdown_path = report_root / f"{_safe_slug(library_id)}_index_report.md"

    scanned_files = iter_files(root_path, include_nested_folders=include_nested)
    records: list[SampleSeedRecord] = []
    unsupported: list[str] = []
    unreadable: list[str] = []

    for source_path in scanned_files:
        extension = source_path.suffix.lower()
        try:
            relative_path = source_path.resolve().relative_to(root_path.resolve()).as_posix()
        except ValueError:
            relative_path = source_path.name
        if extension not in SUPPORTED_EXTENSIONS:
            unsupported.append(relative_path)
            continue

        limitations: list[str] = [
            "classification is heuristic and not ground truth",
            "no deep feature extraction performed in this indexing phase",
        ]
        review_status = "indexed_unreviewed"
        file_size_bytes = 0
        file_hash_sha256: str | None = None
        duration_seconds: float | None = None
        sample_rate: int | None = None
        channels: int | None = None
        fmt: str | None = extension.lstrip(".")
        sample_id = f"{_safe_slug(library_id)}__{relative_path.replace('/', '__')}"

        try:
            file_size_bytes = source_path.stat().st_size
        except OSError as exc:
            review_status = "needs_review"
            unreadable.append(relative_path)
            limitations.append(f"file_size_probe_failed:{type(exc).__name__}")

        if hash_files:
            try:
                file_hash_sha256 = file_sha256(source_path)
            except OSError as exc:
                review_status = "needs_review"
                unreadable.append(relative_path)
                limitations.append(f"hash_failed:{type(exc).__name__}")

        metadata = probe_audio_metadata(source_path)
        if metadata:
            duration_seconds = metadata.get("duration_seconds")
            sample_rate = metadata.get("sample_rate")
            channels = metadata.get("channels")
            fmt = metadata.get("format") or fmt
        else:
            limitations.append("audio_metadata_unavailable")

        if review_status == "needs_review":
            limitations.append("requires_human_review_due_to_read_failure")

        record = build_sample_seed_record(
            sample_id=sample_id,
            library_id=library_id,
            source_path=source_path,
            root_path=root_path,
            extension=extension,
            file_size_bytes=file_size_bytes,
            file_hash_sha256=file_hash_sha256,
            duration_seconds=duration_seconds,
            sample_rate=sample_rate,
            channels=channels,
            fmt=fmt,
            authorization_status=str(config["authorization_status"]),
            review_status=review_status,
            intended_uses=[str(item) for item in config["intended_uses"]],
            limitations=limitations,
        )
        records.append(record)

    records_text = "\n".join(json.dumps(record, ensure_ascii=True) for record in records)
    if records_text:
        records_path.write_text(records_text + "\n", encoding="utf-8")
    else:
        records_path.write_text("", encoding="utf-8")

    report: SampleLibraryIndexReport = {
        "library_id": library_id,
        "source_type": "local_sample_seed_library",
        "root_path": str(root_path.resolve()),
        "generated_at": _now_iso(),
        "files_scanned": len(scanned_files),
        "supported_files_indexed": len(records),
        "unsupported_files_skipped": len(unsupported),
        "unreadable_or_problem_files": len(set(unreadable)),
        "unsupported_files": sorted(set(unsupported)),
        "unreadable_files": sorted(set(unreadable)),
        "notes": [
            "Local sample seed library indexing only (not performance ingestion).",
            "No transcription, no model training, no modal calls, no source file modifications.",
            "Asset typing is conservative heuristic classification and may be unknown.",
        ],
    }

    manifest: SampleLibraryManifest = {
        "library_id": library_id,
        "root_path": str(root_path.resolve()),
        "source_type": "local_sample_seed_library",
        "authorization_status": str(config["authorization_status"]),
        "intended_uses": [str(item) for item in config["intended_uses"]],
        "generated_at": report["generated_at"],
        "file_counts": {
            "files_scanned": report["files_scanned"],
            "supported_files_indexed": report["supported_files_indexed"],
            "unsupported_files_skipped": report["unsupported_files_skipped"],
            "unreadable_or_problem_files": report["unreadable_or_problem_files"],
        },
        "records_path": records_path.resolve().as_posix(),
        "report_json_path": report_json_path.resolve().as_posix(),
        "report_markdown_path": report_markdown_path.resolve().as_posix(),
        "indexing_policy": {
            "do_not_move_source_files": bool(ingestion_policy.get("do_not_move_source_files", True)),
            "do_not_modify_source_files": bool(ingestion_policy.get("do_not_modify_source_files", True)),
            "hash_files": hash_files,
            "include_nested_folders": include_nested,
            "skip_unsupported_files": bool(ingestion_policy.get("skip_unsupported_files", True)),
        },
    }

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_markdown_path.write_text(_build_report_markdown(report), encoding="utf-8")

    return IndexResult(
        manifest_path=manifest_path.resolve(),
        records_path=records_path.resolve(),
        report_json_path=report_json_path.resolve(),
        report_markdown_path=report_markdown_path.resolve(),
        report=report,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Index a local sample seed library without modifying source files.",
        epilog=(
            "Create a local config by copying "
            "config/sample_libraries/local_sounds_library.example.json "
            "to config/sample_libraries/local_sounds_library.json and setting your local root_path."
        ),
    )
    parser.add_argument("config_json", help="Path to sample library config JSON")
    args = parser.parse_args()

    result = index_sample_library(Path(args.config_json))
    print(f"SAMPLE_LIBRARY_MANIFEST_PATH={result.manifest_path.as_posix()}")
    print(f"SAMPLE_SEED_RECORDS_PATH={result.records_path.as_posix()}")
    print(f"INDEX_REPORT_JSON_PATH={result.report_json_path.as_posix()}")
    print(f"INDEX_REPORT_MD_PATH={result.report_markdown_path.as_posix()}")
    print(f"FILES_SCANNED={result.report['files_scanned']}")
    print(f"SUPPORTED_FILES_INDEXED={result.report['supported_files_indexed']}")
    print(f"UNSUPPORTED_FILES_SKIPPED={result.report['unsupported_files_skipped']}")
    print(f"UNREADABLE_OR_PROBLEM_FILES={result.report['unreadable_or_problem_files']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
