from __future__ import annotations

import json
import math
import struct
import wave
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class WavVerificationResult:
    path: str
    exists: bool
    readable: bool
    duration_seconds: float
    nonzero_samples: bool
    sample_rate: int
    bit_depth: int
    channels: int
    peak: float
    rms: float
    clipping_detected: bool
    silence_detected: bool
    render_backend: str
    source_midi_provenance: str


def verify_wav_file(path: Path, render_backend: str = "", source_midi_provenance: str = "") -> WavVerificationResult:
    if not path.exists():
        return WavVerificationResult(
            path=path.as_posix(),
            exists=False,
            readable=False,
            duration_seconds=0.0,
            nonzero_samples=False,
            sample_rate=0,
            bit_depth=0,
            channels=0,
            peak=0.0,
            rms=0.0,
            clipping_detected=False,
            silence_detected=True,
            render_backend=render_backend,
            source_midi_provenance=source_midi_provenance,
        )

    try:
        with wave.open(str(path), "rb") as wav:
            channels = wav.getnchannels()
            sample_rate = wav.getframerate()
            sample_width = wav.getsampwidth()
            frame_count = wav.getnframes()
            raw = wav.readframes(frame_count)
    except Exception:  # noqa: BLE001
        return WavVerificationResult(
            path=path.as_posix(),
            exists=True,
            readable=False,
            duration_seconds=0.0,
            nonzero_samples=False,
            sample_rate=0,
            bit_depth=0,
            channels=0,
            peak=0.0,
            rms=0.0,
            clipping_detected=False,
            silence_detected=True,
            render_backend=render_backend,
            source_midi_provenance=source_midi_provenance,
        )

    if frame_count <= 0 or sample_rate <= 0 or sample_width <= 0:
        return WavVerificationResult(
            path=path.as_posix(),
            exists=True,
            readable=True,
            duration_seconds=0.0,
            nonzero_samples=False,
            sample_rate=sample_rate,
            bit_depth=sample_width * 8,
            channels=channels,
            peak=0.0,
            rms=0.0,
            clipping_detected=False,
            silence_detected=True,
            render_backend=render_backend,
            source_midi_provenance=source_midi_provenance,
        )

    peak_raw, rms_raw = _peak_rms(raw, sample_width)
    max_val = float((2 ** (sample_width * 8 - 1)) - 1)
    peak = (peak_raw / max_val) if max_val else 0.0
    rms = (rms_raw / max_val) if max_val else 0.0
    nonzero = peak_raw > 0 or rms_raw > 0

    return WavVerificationResult(
        path=path.as_posix(),
        exists=True,
        readable=True,
        duration_seconds=frame_count / float(sample_rate),
        nonzero_samples=nonzero,
        sample_rate=sample_rate,
        bit_depth=sample_width * 8,
        channels=channels,
        peak=round(peak, 6),
        rms=round(rms, 6),
        clipping_detected=peak >= 0.9999,
        silence_detected=not nonzero,
        render_backend=render_backend,
        source_midi_provenance=source_midi_provenance,
    )


def _peak_rms(raw: bytes, sample_width: int) -> tuple[int, float]:
    if not raw:
        return 0, 0.0
    if sample_width == 1:
        samples = [int(b) - 128 for b in raw]
    elif sample_width == 2:
        count = len(raw) // 2
        samples = list(struct.unpack("<" + "h" * count, raw[: count * 2]))
    elif sample_width == 4:
        count = len(raw) // 4
        samples = list(struct.unpack("<" + "i" * count, raw[: count * 4]))
    else:
        return 0, 0.0
    if not samples:
        return 0, 0.0
    peak = max(abs(value) for value in samples)
    rms = math.sqrt(sum(value * value for value in samples) / len(samples))
    return int(peak), float(rms)


def write_verification_reports(results: list[WavVerificationResult], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps([asdict(item) for item in results], indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = ["# WAV Render Verification Report", ""]
    if not results:
        lines.append("- no files checked")
    for item in results:
        lines.append(
            f"- `{item.path}` exists=`{item.exists}` readable=`{item.readable}` duration=`{item.duration_seconds:.3f}` "
            f"nonzero=`{item.nonzero_samples}` peak=`{item.peak:.4f}` rms=`{item.rms:.4f}` clipping=`{item.clipping_detected}`"
        )
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
