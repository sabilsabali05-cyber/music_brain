from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.ingest_performance import ingest_performance
from scripts.process_performance import process_performance_manifest

SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a"}


def _discover_audio_files(inbox_folder: Path) -> list[Path]:
    return sorted(
        [
            path
            for path in inbox_folder.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
        ]
    )


def _find_existing_manifest(source_path: Path, library_root: Path) -> Path | None:
    for candidate in library_root.glob("*/performance_manifest.json"):
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if str(payload.get("source_path", "")) == source_path.resolve().as_posix():
            return candidate.resolve()
    return None


def batch_performances(inbox_folder: Path, *, max_performances: int = 1, max_windows: int = 3) -> Path:
    inbox_folder.mkdir(parents=True, exist_ok=True)
    library_root = Path("performances") / "library"
    reports_root = Path("performances") / "reports"
    library_root.mkdir(parents=True, exist_ok=True)
    reports_root.mkdir(parents=True, exist_ok=True)

    files = _discover_audio_files(inbox_folder)
    print(f"batch_files_discovered: {len(files)}")
    print(f"batch_max_performances: {max_performances}")
    print(f"batch_max_windows: {max_windows}")
    print("batch_calls_modal: yes (analysis + transcription)")
    print("batch_warning: running cautious staged processing; increase limits deliberately.")

    processed: list[dict[str, object]] = []
    for source_path in files[:max_performances]:
        existing = _find_existing_manifest(source_path, library_root)
        manifest_path = existing if existing else ingest_performance(source_path)
        status = "processed"
        error = None
        try:
            process_performance_manifest(
                manifest_path,
                max_windows=max_windows,
                resume=True,
            )
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            error = f"{exc.__class__.__name__}: {exc}"
        processed.append(
            {
                "source_path": source_path.resolve().as_posix(),
                "performance_manifest_path": Path(manifest_path).resolve().as_posix(),
                "status": status,
                "error": error,
            }
        )

    report_path = reports_root / f"batch_report_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}.json"
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "inbox_folder": inbox_folder.resolve().as_posix(),
        "files_discovered": len(files),
        "max_performances": max_performances,
        "max_windows": max_windows,
        "processed": processed,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch ingest and process long performance audio files.")
    parser.add_argument("inbox_folder", help="Path to performances/inbox")
    parser.add_argument("--max-performances", type=int, default=1)
    parser.add_argument("--max-windows", type=int, default=3)
    args = parser.parse_args()
    report_path = batch_performances(
        Path(args.inbox_folder),
        max_performances=args.max_performances,
        max_windows=args.max_windows,
    )
    print(f"BATCH_REPORT_PATH={report_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
