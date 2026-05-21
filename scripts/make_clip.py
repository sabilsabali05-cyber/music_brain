from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def make_clip(input_audio: Path, *, start: float = 0.0, seconds: float = 30.0) -> Path:
    if not input_audio.exists():
        raise FileNotFoundError(f"Input audio not found: {input_audio.as_posix()}")
    if seconds <= 0:
        raise ValueError("--seconds must be > 0")
    if start < 0:
        raise ValueError("--start must be >= 0")

    ffmpeg_exe = shutil.which("ffmpeg")
    if not ffmpeg_exe:
        raise RuntimeError("ffmpeg not found on PATH")

    clips_dir = Path("samples") / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    suffix = input_audio.suffix.lower() or ".wav"
    output_path = clips_dir / f"{input_audio.stem}_clip_{int(start)}s_{int(seconds)}s{suffix}"

    command = [
        ffmpeg_exe,
        "-y",
        "-ss",
        f"{start}",
        "-t",
        f"{seconds}",
        "-i",
        str(input_audio),
        "-vn",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(f"ffmpeg failed while creating clip: {stderr or 'unknown ffmpeg error'}")

    return output_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a short audio clip using ffmpeg.")
    parser.add_argument("input_audio", help="Path to the source audio file.")
    parser.add_argument("--start", type=float, default=0.0, help="Start offset in seconds (default: 0).")
    parser.add_argument("--seconds", type=float, default=30.0, help="Clip length in seconds (default: 30).")
    args = parser.parse_args()

    clip_path = make_clip(Path(args.input_audio), start=args.start, seconds=args.seconds)
    print(clip_path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
