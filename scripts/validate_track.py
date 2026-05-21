from __future__ import annotations

import json
import sys
from pathlib import Path

from mido import MidiFile


def validate_track(track_folder: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    info: list[str] = []

    report_path = track_folder / "analysis" / "job_report.json"
    normalized_path = track_folder / "original" / "normalized.wav"
    midi_path = track_folder / "midi" / "full_mix.mid"

    if not report_path.exists():
        errors.append(f"Missing file: {report_path.as_posix()}")
        return False, errors

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Could not parse job report JSON: {exc.__class__.__name__}: {exc}")
        return False, errors

    if report.get("status") != "success":
        errors.append(f"Expected status=success, got {report.get('status')!r}")
    if report.get("provider_used") != "yourmt3":
        errors.append(f"Expected provider_used=yourmt3, got {report.get('provider_used')!r}")
    if report.get("backend") != "modal":
        errors.append(f"Expected backend=modal, got {report.get('backend')!r}")
    if report.get("fallback_used") is not False:
        errors.append(f"Expected fallback_used=false, got {report.get('fallback_used')!r}")

    if not normalized_path.exists():
        errors.append(f"Missing file: {normalized_path.as_posix()}")
    if not midi_path.exists():
        errors.append(f"Missing file: {midi_path.as_posix()}")

    if midi_path.exists():
        midi_size = midi_path.stat().st_size
        if midi_size <= 0:
            errors.append(f"MIDI file is empty: {midi_path.as_posix()}")
        else:
            info.append(f"MIDI bytes: {midi_size}")
        try:
            midi = MidiFile(str(midi_path))
            track_count = len(midi.tracks)
            message_count = sum(len(track) for track in midi.tracks)
            info.append(f"MIDI parse ok: tracks={track_count}, messages={message_count}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"MIDI parse failed: {exc.__class__.__name__}: {exc}")

    return len(errors) == 0, info + errors


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_track.py <track-folder>")
        return 1

    track_folder = Path(sys.argv[1]).resolve()
    print(f"Validating track: {track_folder.as_posix()}")

    ok, messages = validate_track(track_folder)
    for message in messages:
        print(f"- {message}")

    if ok:
        print("Validation result: PASS")
        return 0

    print("Validation result: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
