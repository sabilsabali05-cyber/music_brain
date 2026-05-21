from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import wave
from datetime import datetime, timezone
from pathlib import Path


def safe_source_name(path: Path) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", path.stem).strip("_") or "performance"


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


def extract_analysis_wav(source_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-ac",
        "1",
        "-ar",
        "22050",
        "-vn",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg wav conversion failed: {(result.stderr or '').strip()}")


def _normalize_curve(values: list[float]) -> list[float]:
    if not values:
        return []
    low = min(values)
    high = max(values)
    if high - low <= 1e-9:
        return [0.0 for _ in values]
    return [(v - low) / (high - low) for v in values]


def _simple_derivative(values: list[float]) -> list[float]:
    if not values:
        return []
    result = [0.0]
    for idx in range(1, len(values)):
        result.append(abs(values[idx] - values[idx - 1]))
    return result


def _peak_pick(values: list[float], threshold: float, min_distance_frames: int) -> list[int]:
    peaks: list[int] = []
    last_peak = -min_distance_frames
    for idx in range(1, len(values) - 1):
        if idx - last_peak < min_distance_frames:
            continue
        current = values[idx]
        if current < threshold:
            continue
        if current >= values[idx - 1] and current >= values[idx + 1]:
            peaks.append(idx)
            last_peak = idx
    return peaks


def _feature_value(curve: list[float], index: int) -> float:
    if not curve:
        return 0.0
    if index < 0:
        return float(curve[0])
    if index >= len(curve):
        return float(curve[-1])
    return float(curve[index])


def _read_wav_samples(wav_path: Path) -> tuple[list[float], int]:
    with wave.open(str(wav_path), "rb") as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        sample_width = wav.getsampwidth()
        frame_count = wav.getnframes()
        raw = wav.readframes(frame_count)
    if sample_width != 2:
        raise RuntimeError("Only 16-bit PCM WAV is supported for audio structure analysis.")

    try:
        import numpy as np  # type: ignore
    except Exception:
        np = None

    if np is not None:
        arr = np.frombuffer(raw, dtype=np.int16)
        if channels > 1:
            arr = arr.reshape((-1, channels)).mean(axis=1)
        samples = (arr / 32768.0).astype(float).tolist()
        return samples, sample_rate

    samples: list[float] = []
    step = 2 * channels
    for start in range(0, len(raw), step):
        if start + step > len(raw):
            break
        mono = int.from_bytes(raw[start : start + 2], byteorder="little", signed=True)
        samples.append(float(mono) / 32768.0)
    return samples, sample_rate


def _compute_features(
    samples: list[float], sample_rate: int, frame_hop_seconds: float
) -> tuple[dict[str, list[float]], list[str], list[str]]:
    frame_size = max(256, int(sample_rate * frame_hop_seconds * 2.0))
    hop_size = max(128, int(sample_rate * frame_hop_seconds))
    if len(samples) < frame_size:
        padded = samples + [0.0] * (frame_size - len(samples))
        samples = padded

    try:
        import numpy as np  # type: ignore
    except Exception:
        np = None

    rms: list[float] = []
    onset_strength: list[float] = []
    chroma_change: list[float] = []
    timbre_change: list[float] = []

    if np is None:
        for start in range(0, len(samples) - frame_size + 1, hop_size):
            frame = samples[start : start + frame_size]
            energy = math.sqrt(sum(v * v for v in frame) / max(1, len(frame)))
            rms.append(energy)
        onset_strength = _simple_derivative(_normalize_curve(rms))
        novelty_combined = _normalize_curve(onset_strength)
        features = {
            "rms": _normalize_curve(rms),
            "onset_strength": _normalize_curve(onset_strength),
            "chroma_change": [],
            "timbre_change": [],
            "novelty_combined": novelty_combined,
        }
        return features, ["rms", "onset_strength"], ["chroma_change", "timbre_change"]

    sample_np = np.array(samples, dtype=np.float32)
    freqs = np.fft.rfftfreq(frame_size, d=1.0 / sample_rate)
    previous_chroma = None
    previous_centroid = None
    for start in range(0, len(sample_np) - frame_size + 1, hop_size):
        frame = sample_np[start : start + frame_size]
        rms_value = float(np.sqrt(np.mean(frame * frame)))
        rms.append(rms_value)

        spectrum = np.abs(np.fft.rfft(frame))
        spectrum_sum = float(np.sum(spectrum)) + 1e-9
        centroid = float(np.sum(freqs * spectrum) / spectrum_sum)

        chroma = np.zeros(12, dtype=np.float32)
        for idx, freq in enumerate(freqs):
            if freq <= 20.0:
                continue
            midi = 69 + 12 * math.log2(freq / 440.0)
            pitch_class = int(round(midi)) % 12
            chroma[pitch_class] += float(spectrum[idx])
        chroma_norm = float(np.sum(chroma)) + 1e-9
        chroma = chroma / chroma_norm

        if previous_chroma is None:
            chroma_change.append(0.0)
        else:
            chroma_change.append(float(np.sum(np.abs(chroma - previous_chroma))))
        previous_chroma = chroma

        if previous_centroid is None:
            timbre_change.append(0.0)
        else:
            timbre_change.append(abs(centroid - previous_centroid))
        previous_centroid = centroid

    onset_strength = _simple_derivative(_normalize_curve(rms))
    chroma_change = _normalize_curve(chroma_change)
    timbre_change = _normalize_curve(timbre_change)
    rms_norm = _normalize_curve(rms)
    onset_norm = _normalize_curve(onset_strength)

    novelty_combined: list[float] = []
    for idx in range(len(rms_norm)):
        novelty_combined.append(
            (
                0.30 * _feature_value(onset_norm, idx)
                + 0.25 * _feature_value(chroma_change, idx)
                + 0.25 * _feature_value(timbre_change, idx)
                + 0.20 * _feature_value(rms_norm, idx)
            )
        )
    novelty_combined = _normalize_curve(novelty_combined)

    features = {
        "rms": rms_norm,
        "onset_strength": onset_norm,
        "chroma_change": chroma_change,
        "timbre_change": timbre_change,
        "novelty_combined": novelty_combined,
    }
    return features, ["rms", "onset_strength", "chroma_change", "timbre_change"], []


def fuse_boundary_candidates(
    *,
    feature_curves: dict[str, list[float]],
    frame_hop_seconds: float,
    duration_seconds: float,
    target_window_seconds: float = 60.0,
    max_window_seconds: float = 90.0,
    min_segment_seconds: float = 12.0,
    confidence_threshold: float = 0.55,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    combined = feature_curves.get("novelty_combined", [])
    if not combined:
        combined = _normalize_curve(
            [
                (_feature_value(feature_curves.get("rms", []), i) + _feature_value(feature_curves.get("onset_strength", []), i))
                / 2.0
                for i in range(max(len(feature_curves.get("rms", [])), len(feature_curves.get("onset_strength", []))))
            ]
        )

    min_distance_frames = max(1, int(min_segment_seconds / frame_hop_seconds))
    raw_peaks = _peak_pick(combined, threshold=confidence_threshold, min_distance_frames=min_distance_frames)
    raw_candidates: list[dict[str, object]] = []
    for peak in raw_peaks:
        time_seconds = min(duration_seconds, peak * frame_hop_seconds)
        evidence = {
            "energy_change": round(_feature_value(feature_curves.get("rms", []), peak), 6),
            "onset_change": round(_feature_value(feature_curves.get("onset_strength", []), peak), 6),
            "chroma_change": round(_feature_value(feature_curves.get("chroma_change", []), peak), 6),
            "timbre_change": round(_feature_value(feature_curves.get("timbre_change", []), peak), 6),
            "combined_novelty": round(_feature_value(combined, peak), 6),
        }
        dominant = max(
            [
                ("harmonic_chroma_change", evidence["chroma_change"]),
                ("timbre_change", evidence["timbre_change"]),
                ("onset_density_change", evidence["onset_change"]),
                ("combined_audio_novelty", evidence["combined_novelty"]),
            ],
            key=lambda item: item[1],
        )[0]
        raw_candidates.append(
            {
                "time_seconds": round(time_seconds, 6),
                "confidence": round(float(evidence["combined_novelty"]), 3),
                "reason": dominant,
                "feature_evidence": evidence,
            }
        )

    accepted: list[dict[str, object]] = []
    accepted_raw_count = 0
    start = 0.0
    while start < duration_seconds:
        remaining = duration_seconds - start
        if remaining <= max_window_seconds:
            break
        lower = start + min_segment_seconds
        upper = min(duration_seconds, start + max_window_seconds)
        local = [c for c in raw_candidates if lower <= float(c["time_seconds"]) <= upper]
        if local:
            target = start + target_window_seconds
            chosen = max(
                local,
                key=lambda c: (
                    float(c["confidence"]) - (abs(float(c["time_seconds"]) - target) / max(1.0, target_window_seconds))
                ),
            )
            accepted.append(chosen)
            accepted_raw_count += 1
            start = float(chosen["time_seconds"])
            continue

        fixed_time = min(duration_seconds, start + target_window_seconds)
        accepted.append(
            {
                "time_seconds": round(fixed_time, 6),
                "confidence": 0.2,
                "reason": "fixed_interval_fallback",
                "feature_evidence": {
                    "energy_change": 0.0,
                    "onset_change": 0.0,
                    "chroma_change": 0.0,
                    "timbre_change": 0.0,
                    "combined_novelty": 0.2,
                },
            }
        )
        start = fixed_time

    fallback_recommended = accepted_raw_count == 0
    diagnostics = {
        "raw_peak_count": len(raw_candidates),
        "candidate_boundary_count": len(accepted),
        "accepted_boundary_count": accepted_raw_count,
        "rejected_boundary_count": max(0, len(raw_candidates) - accepted_raw_count),
        "fallback_recommended": fallback_recommended,
    }
    return accepted, diagnostics


def analyze_audio_structure(source_path: Path) -> Path:
    if not source_path.exists():
        raise FileNotFoundError(f"Audio file does not exist: {source_path}")

    source_safe = safe_source_name(source_path)
    analysis_root = Path("samples") / "analysis" / source_safe
    analysis_root.mkdir(parents=True, exist_ok=True)
    analysis_path = analysis_root / "structure_analysis.json"
    wav_path = analysis_root / "analysis_audio.wav"

    frame_hop_seconds = 0.25
    duration_seconds = probe_duration_seconds(source_path)
    extract_analysis_wav(source_path, wav_path)
    samples, sample_rate = _read_wav_samples(wav_path)
    features, available_features, missing_features = _compute_features(samples, sample_rate, frame_hop_seconds)
    candidates, fusion = fuse_boundary_candidates(
        feature_curves=features,
        frame_hop_seconds=frame_hop_seconds,
        duration_seconds=duration_seconds,
    )

    notes: list[str] = [
        "Boundary candidates are conservative signals, not ground-truth phrases.",
        "Use fallback segmentation when confidence is low or candidate coverage is sparse.",
    ]
    if missing_features:
        notes.append("Some advanced features unavailable in current environment; conservative fallback recommended.")

    payload = {
        "source_path": source_path.resolve().as_posix(),
        "source_name": source_path.name,
        "duration_seconds": round(duration_seconds, 6),
        "analysis_version": "audio_structure_v1",
        "frame_hop_seconds": frame_hop_seconds,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "features": features,
        "boundary_candidates": candidates,
        "diagnostics": {
            "fallback_recommended": bool(fusion["fallback_recommended"]),
            "candidate_boundary_count": int(fusion["candidate_boundary_count"]),
            "accepted_boundary_count": int(fusion["accepted_boundary_count"]),
            "rejected_boundary_count": int(fusion["rejected_boundary_count"]),
            "available_features": available_features,
            "missing_features": missing_features,
            "notes": notes,
        },
    }
    analysis_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return analysis_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze pre-MIDI audio structure and boundary candidates.")
    parser.add_argument("source_path", help="Path to input audio.")
    args = parser.parse_args()
    analysis_path = analyze_audio_structure(Path(args.source_path))
    print(f"ANALYSIS_PATH={analysis_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
