from __future__ import annotations

import hashlib
import subprocess
import wave
from pathlib import Path


class AudioProcessingError(RuntimeError):
    pass


def checksum_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def convert_to_normalized_wav(input_path: Path, output_path: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ac",
        "2",
        "-ar",
        "44100",
        "-sample_fmt",
        "s16",
        "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11",
        str(output_path),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AudioProcessingError(
            "ffmpeg binary was not found. Install ffmpeg and make sure it is on PATH."
        ) from exc

    if result.returncode != 0:
        raise AudioProcessingError(
            "ffmpeg conversion failed.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        frame_count = handle.getnframes()
        frame_rate = handle.getframerate()
    if frame_rate <= 0:
        return 0.0
    return frame_count / float(frame_rate)
