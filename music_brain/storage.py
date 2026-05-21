from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrackPaths:
    track_root: Path
    original_dir: Path
    midi_dir: Path
    analysis_dir: Path
    input_audio: Path
    normalized_audio: Path
    full_mix_midi: Path
    job_report: Path


class TrackStorage:
    def __init__(self, library_root: Path) -> None:
        self.library_root = library_root

    def build_paths(self, track_id: str, input_filename: str) -> TrackPaths:
        track_root = self.library_root / track_id
        original_dir = track_root / "original"
        midi_dir = track_root / "midi"
        analysis_dir = track_root / "analysis"
        return TrackPaths(
            track_root=track_root,
            original_dir=original_dir,
            midi_dir=midi_dir,
            analysis_dir=analysis_dir,
            input_audio=original_dir / input_filename,
            normalized_audio=original_dir / "normalized.wav",
            full_mix_midi=midi_dir / "full_mix.mid",
            job_report=analysis_dir / "job_report.json",
        )

    @staticmethod
    def ensure_directories(paths: TrackPaths) -> None:
        paths.original_dir.mkdir(parents=True, exist_ok=True)
        paths.midi_dir.mkdir(parents=True, exist_ok=True)
        paths.analysis_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def copy_input(source: Path, destination: Path) -> None:
        shutil.copy2(source, destination)
