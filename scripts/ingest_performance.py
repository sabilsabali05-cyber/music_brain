from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def safe_slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("_") or "performance"


def probe_duration_seconds(source_path: Path) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(source_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {(result.stderr or '').strip()}")
    return float((result.stdout or "").strip())


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def ingest_performance(source_path: Path) -> Path:
    if not source_path.exists():
        raise FileNotFoundError(f"Performance audio does not exist: {source_path}")

    inbox = Path("performances") / "inbox"
    library = Path("performances") / "library"
    reports = Path("performances") / "reports"
    inbox.mkdir(parents=True, exist_ok=True)
    library.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now(timezone.utc)
    performance_id = f"{created_at.strftime('%Y%m%dT%H%M%S%f')}_{safe_slug(source_path.stem)}"
    performance_dir = library / performance_id
    performance_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = performance_dir / "performance_manifest.json"

    payload = {
        "performance_id": performance_id,
        "source_path": source_path.resolve().as_posix(),
        "source_name": source_path.name,
        "duration_seconds": round(probe_duration_seconds(source_path), 6),
        "checksum": file_sha256(source_path),
        "created_at": created_at.isoformat(),
        "status": "ingested",
        "analysis_path": None,
        "segments_manifest_path": None,
        "merged_midi_path": None,
        "active_analysis_path": None,
        "active_segments_manifest_path": None,
        "active_merged_midi_path": None,
        "run_history": [],
        "reports": {
            "review_report_path": None,
            "benchmark_summary": None,
            "batch_report_path": None,
        },
        "steps": {
            "analysis": {"status": "pending", "updated_at": created_at.isoformat()},
            "segmentation": {"status": "pending", "updated_at": created_at.isoformat()},
            "transcription": {"status": "pending", "updated_at": created_at.isoformat()},
            "benchmark": {"status": "pending", "updated_at": created_at.isoformat()},
            "review": {"status": "pending", "updated_at": created_at.isoformat()},
            "stitch": {"status": "pending", "updated_at": created_at.isoformat()},
        },
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest a long performance into the batch processing library.")
    parser.add_argument("source_path", help="Path to performance audio file")
    args = parser.parse_args()
    manifest_path = ingest_performance(Path(args.source_path))
    print(f"PERFORMANCE_MANIFEST_PATH={manifest_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
