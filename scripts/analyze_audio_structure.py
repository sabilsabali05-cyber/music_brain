from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

FEATURE_REASON_MAP: dict[str, str] = {
    "novelty_combined": "combined_audio_novelty",
    "chroma_change": "harmonic_chroma_change",
    "timbre_change": "timbre_change",
    "onset_strength": "onset_density_change",
    "rms": "energy_change",
}

DENSITY_PRESETS: dict[str, dict[str, float]] = {
    "conservative": {"threshold_offset": 0.05, "distance_scale": 1.2, "max_scale": 0.8},
    "normal": {"threshold_offset": 0.0, "distance_scale": 1.0, "max_scale": 1.0},
    "dense": {"threshold_offset": -0.12, "distance_scale": 0.55, "max_scale": 1.8},
}


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
    candidate_density: str = "conservative",
    peak_pick_threshold: float = 0.55,
    min_boundary_distance_seconds: float = 12.0,
    max_candidates: int = 8,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    _ = target_window_seconds
    _ = max_window_seconds
    density = str(candidate_density).lower().strip() or "conservative"
    if density not in DENSITY_PRESETS:
        density = "conservative"
    preset = DENSITY_PRESETS[density]
    requested_threshold = float(peak_pick_threshold)
    effective_threshold = max(0.0, min(1.0, requested_threshold + float(preset["threshold_offset"])))
    requested_min_distance_seconds = max(0.1, float(min_boundary_distance_seconds))
    effective_min_distance_seconds = max(0.1, requested_min_distance_seconds * float(preset["distance_scale"]))
    effective_max_candidates = max(1, int(round(max(1, int(max_candidates)) * float(preset["max_scale"]))))
    min_distance_frames = max(1, int(effective_min_distance_seconds / max(frame_hop_seconds, 1e-6)))

    normalized_curves = {
        "novelty_combined": feature_curves.get("novelty_combined", []),
        "chroma_change": feature_curves.get("chroma_change", []),
        "timbre_change": feature_curves.get("timbre_change", []),
        "onset_strength": feature_curves.get("onset_strength", []),
        "rms": feature_curves.get("rms", []),
    }
    if not normalized_curves["novelty_combined"]:
        normalized_curves["novelty_combined"] = _normalize_curve(
            [
                (_feature_value(normalized_curves["rms"], i) + _feature_value(normalized_curves["onset_strength"], i))
                / 2.0
                for i in range(max(len(normalized_curves["rms"]), len(normalized_curves["onset_strength"])))
            ]
        )

    raw_peak_count_by_feature: dict[str, int] = {}
    raw_candidates: list[dict[str, object]] = []
    for source_feature, curve in normalized_curves.items():
        if not curve:
            raw_peak_count_by_feature[source_feature] = 0
            continue
        peaks = _peak_pick(curve, threshold=effective_threshold, min_distance_frames=min_distance_frames)
        raw_peak_count_by_feature[source_feature] = len(peaks)
        for peak in peaks:
            time_seconds = min(duration_seconds, peak * frame_hop_seconds)
            evidence = {
                "energy_change": round(_feature_value(normalized_curves.get("rms", []), peak), 6),
                "onset_change": round(_feature_value(normalized_curves.get("onset_strength", []), peak), 6),
                "chroma_change": round(_feature_value(normalized_curves.get("chroma_change", []), peak), 6),
                "timbre_change": round(_feature_value(normalized_curves.get("timbre_change", []), peak), 6),
                "combined_novelty": round(_feature_value(normalized_curves.get("novelty_combined", []), peak), 6),
            }
            base_confidence = float(_feature_value(curve, peak))
            combined_novelty = float(evidence["combined_novelty"])
            confidence = max(0.0, min(1.0, 0.65 * base_confidence + 0.35 * combined_novelty))
            raw_candidates.append(
                {
                    "time_seconds": round(float(time_seconds), 6),
                    "confidence": round(confidence, 6),
                    "reason": FEATURE_REASON_MAP.get(source_feature, "combined_audio_novelty"),
                    "source_feature": source_feature,
                    "candidate_source": "audio_structure",
                    "eligible_for_phrase_boundary": True,
                    "feature_evidence": evidence,
                }
            )

    raw_candidates.sort(key=lambda row: float(row.get("time_seconds", 0.0)))
    duplicate_window_seconds = max(frame_hop_seconds * 2.0, min(2.0, effective_min_distance_seconds * 0.25))
    grouped: list[list[dict[str, object]]] = []
    for candidate in raw_candidates:
        if not grouped:
            grouped.append([candidate])
            continue
        previous_time = float(grouped[-1][-1].get("time_seconds", 0.0))
        current_time = float(candidate.get("time_seconds", 0.0))
        if abs(current_time - previous_time) <= duplicate_window_seconds:
            grouped[-1].append(candidate)
        else:
            grouped.append([candidate])

    fused_candidates: list[dict[str, object]] = []
    for group_index, group in enumerate(grouped, start=1):
        strongest = max(group, key=lambda row: float(row.get("confidence", 0.0)))
        contributing_features = sorted(
            {str(row.get("source_feature", "novelty_combined")) for row in group if isinstance(row, dict)}
        )
        multi_feature_bonus = 0.04 * max(0, len(contributing_features) - 1)
        boosted_confidence = min(1.0, float(strongest.get("confidence", 0.0)) + multi_feature_bonus)
        merged_evidence = {"energy_change": 0.0, "onset_change": 0.0, "chroma_change": 0.0, "timbre_change": 0.0, "combined_novelty": 0.0}
        for row in group:
            evidence_obj = row.get("feature_evidence", {})
            if not isinstance(evidence_obj, dict):
                continue
            for key in merged_evidence:
                merged_evidence[key] = max(float(merged_evidence[key]), float(evidence_obj.get(key, 0.0) or 0.0))
        fused = dict(strongest)
        fused["confidence"] = round(boosted_confidence, 6)
        fused["duplicate_group_id"] = f"grp_{group_index:04d}"
        fused["contributing_features"] = contributing_features
        fused["feature_evidence"] = {key: round(value, 6) for key, value in merged_evidence.items()}
        fused_candidates.append(fused)

    fused_by_strength = sorted(
        fused_candidates, key=lambda row: float(row.get("confidence", 0.0)), reverse=True
    )
    selected: list[dict[str, object]] = []
    for row in fused_by_strength:
        if len(selected) >= effective_max_candidates:
            break
        time_seconds = float(row.get("time_seconds", 0.0))
        if any(abs(time_seconds - float(existing.get("time_seconds", 0.0))) < effective_min_distance_seconds for existing in selected):
            continue
        selected.append(row)
    selected = sorted(selected, key=lambda row: float(row.get("confidence", 0.0)), reverse=True)
    for index, row in enumerate(selected, start=1):
        row["rank"] = index
    returned = sorted(selected, key=lambda row: float(row.get("time_seconds", 0.0)))

    fallback_recommended = len(returned) == 0
    diagnostics = {
        "candidate_density": density,
        "raw_peak_count_by_feature": raw_peak_count_by_feature,
        "fused_candidate_count": len(fused_candidates),
        "returned_candidate_count": len(returned),
        "peak_pick_threshold": requested_threshold,
        "effective_peak_pick_threshold": round(effective_threshold, 6),
        "min_boundary_distance_seconds": requested_min_distance_seconds,
        "effective_min_boundary_distance_seconds": round(effective_min_distance_seconds, 6),
        "max_candidates": int(max_candidates),
        "effective_max_candidates": int(effective_max_candidates),
        "candidate_boundary_count": len(returned),
        "accepted_boundary_count": 0,
        "rejected_boundary_count": max(0, len(raw_candidates) - len(returned)),
        "fallback_recommended": fallback_recommended,
    }
    return returned, diagnostics


def analyze_audio_structure(
    source_path: Path,
    *,
    candidate_density: str = "conservative",
    peak_pick_threshold: float = 0.55,
    min_boundary_distance_seconds: float = 12.0,
    max_candidates: int = 8,
) -> Path:
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
        candidate_density=candidate_density,
        peak_pick_threshold=peak_pick_threshold,
        min_boundary_distance_seconds=min_boundary_distance_seconds,
        max_candidates=max_candidates,
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
        "analysis_backend": "local_light",
        "frame_hop_seconds": frame_hop_seconds,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "features": features,
        "boundary_candidates": candidates,
        "diagnostics": {
            "fallback_recommended": bool(fusion["fallback_recommended"]),
            "candidate_boundary_count": int(fusion["candidate_boundary_count"]),
            "candidate_density": fusion.get("candidate_density"),
            "raw_peak_count_by_feature": fusion.get("raw_peak_count_by_feature"),
            "fused_candidate_count": int(fusion.get("fused_candidate_count", 0)),
            "returned_candidate_count": int(fusion.get("returned_candidate_count", 0)),
            "peak_pick_threshold": fusion.get("peak_pick_threshold"),
            "min_boundary_distance_seconds": fusion.get("min_boundary_distance_seconds"),
            "max_candidates": fusion.get("max_candidates"),
            "accepted_boundary_count": int(fusion["accepted_boundary_count"]),
            "rejected_boundary_count": int(fusion["rejected_boundary_count"]),
            "available_features": available_features,
            "missing_features": missing_features,
            "notes": notes,
        },
    }
    analysis_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return analysis_path.resolve()


def _invoke_modal_librosa_analysis(
    audio_bytes: bytes, source_name: str, options: dict[str, object]
) -> dict[str, object]:
    try:
        import modal  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "modal package is required for backend=modal_librosa. Install dependencies and run `modal setup`."
        ) from exc
    function = modal.Function.from_name("music-brain-v2", "analyze_audio_structure_modal")
    payload = function.remote(audio_bytes, source_name, options)
    if not isinstance(payload, dict):
        raise RuntimeError("Modal librosa analysis returned invalid payload type.")
    return payload


def analyze_audio_structure_modal(
    source_path: Path,
    *,
    options: dict[str, object] | None = None,
    remote_call: Callable[[bytes, str, dict[str, object]], dict[str, object]] | None = None,
) -> Path:
    if not source_path.exists():
        raise FileNotFoundError(f"Audio file does not exist: {source_path}")

    source_safe = safe_source_name(source_path)
    analysis_root = Path("samples") / "analysis" / source_safe
    analysis_root.mkdir(parents=True, exist_ok=True)
    analysis_path = analysis_root / "structure_analysis.json"
    duration_seconds = probe_duration_seconds(source_path)

    call = remote_call or _invoke_modal_librosa_analysis
    payload = call(source_path.read_bytes(), source_path.name, options or {})
    payload = dict(payload)
    payload["source_path"] = source_path.resolve().as_posix()
    payload["source_name"] = source_path.name
    payload["duration_seconds"] = round(float(payload.get("duration_seconds", duration_seconds)), 6)
    payload["analysis_backend"] = "modal_librosa"
    payload["analysis_version"] = str(payload.get("analysis_version", "audio_structure_modal_librosa_v1"))
    payload["created_at"] = datetime.now(timezone.utc).isoformat()
    if not isinstance(payload.get("features"), dict):
        payload["features"] = {}
    if not isinstance(payload.get("boundary_candidates"), list):
        payload["boundary_candidates"] = []
    normalized_candidates: list[dict[str, object]] = []
    for candidate in payload["boundary_candidates"]:
        if not isinstance(candidate, dict):
            continue
        normalized = dict(candidate)
        source = str(normalized.get("candidate_source", "audio_structure"))
        normalized["candidate_source"] = source
        if "eligible_for_phrase_boundary" not in normalized:
            normalized["eligible_for_phrase_boundary"] = source == "audio_structure"
        normalized["source_feature"] = str(normalized.get("source_feature", "novelty_combined"))
        contributing = normalized.get("contributing_features", [normalized["source_feature"]])
        if not isinstance(contributing, list):
            contributing = [str(contributing)]
        normalized["contributing_features"] = [str(item) for item in contributing]
        if "rank" not in normalized:
            normalized["rank"] = len(normalized_candidates) + 1
        normalized_candidates.append(normalized)
    payload["boundary_candidates"] = normalized_candidates
    diagnostics = payload.get("diagnostics", {})
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    diagnostics.setdefault("available_features", ["rms", "onset_strength", "chroma_change", "timbre_change"])
    diagnostics.setdefault("missing_features", [])
    diagnostics.setdefault("fallback_recommended", False)
    diagnostics.setdefault("candidate_density", (options or {}).get("candidate_density", "conservative"))
    diagnostics.setdefault("raw_peak_count_by_feature", {})
    diagnostics.setdefault("fused_candidate_count", len(normalized_candidates))
    diagnostics.setdefault("returned_candidate_count", len(normalized_candidates))
    diagnostics.setdefault("peak_pick_threshold", (options or {}).get("peak_pick_threshold", 0.55))
    diagnostics.setdefault(
        "min_boundary_distance_seconds", (options or {}).get("min_boundary_distance_seconds", 12.0)
    )
    diagnostics.setdefault("max_candidates", (options or {}).get("max_candidates", 8))
    diagnostics.setdefault("notes", ["Computed on Modal CPU librosa backend."])
    payload["diagnostics"] = diagnostics
    analysis_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return analysis_path.resolve()


def audio_analysis_diagnostics() -> dict[str, object]:
    diagnostics: dict[str, object] = {
        "modal_auth_configured": False,
        "modal_librosa_function_lookup_ok": False,
        "local_light_available": False,
        "modal_librosa_cpu_only": True,
        "notes": [],
    }
    has_env_auth = bool(
        (os.getenv("MODAL_TOKEN_ID") or "").strip() and (os.getenv("MODAL_TOKEN_SECRET") or "").strip()
    )
    has_file_auth = (Path.home() / ".modal.toml").exists()
    diagnostics["modal_auth_configured"] = has_env_auth or has_file_auth

    try:
        import modal  # type: ignore[import-not-found]

        modal.Function.from_name("music-brain-v2", "analyze_audio_structure_modal")
        diagnostics["modal_librosa_function_lookup_ok"] = True
    except Exception as exc:  # noqa: BLE001
        diagnostics["notes"].append(f"Modal function lookup failed: {exc.__class__.__name__}: {exc}")

    try:
        import numpy  # type: ignore

        diagnostics["local_light_available"] = True
        diagnostics["notes"].append("Local analyzer has numpy available for lightweight feature extraction.")
    except Exception:
        diagnostics["local_light_available"] = True
        diagnostics["notes"].append("Local analyzer will run without numpy using minimal RMS/onset fallback.")

    diagnostics["notes"].append("Modal librosa analyzer runs on CPU image and does not require GPU.")
    return diagnostics


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze pre-MIDI audio structure and boundary candidates.")
    parser.add_argument("source_path", nargs="?", help="Path to input audio.")
    parser.add_argument("--backend", choices=["local_light", "modal_librosa"], default="local_light")
    parser.add_argument("--candidate-density", choices=["conservative", "normal", "dense"], default="conservative")
    parser.add_argument("--peak-pick-threshold", type=float, default=0.55)
    parser.add_argument("--min-boundary-distance-seconds", type=float, default=12.0)
    parser.add_argument("--max-candidates", type=int, default=8)
    parser.add_argument("--diagnostics", action="store_true")
    args = parser.parse_args()

    if args.diagnostics:
        print(json.dumps(audio_analysis_diagnostics(), indent=2))
        return 0

    if not args.source_path:
        raise SystemExit("source_path is required unless --diagnostics is provided")

    options = {
        "candidate_density": args.candidate_density,
        "peak_pick_threshold": float(args.peak_pick_threshold),
        "min_boundary_distance_seconds": float(args.min_boundary_distance_seconds),
        "max_candidates": int(args.max_candidates),
    }
    if args.backend == "modal_librosa":
        analysis_path = analyze_audio_structure_modal(Path(args.source_path), options=options)
    else:
        analysis_path = analyze_audio_structure(
            Path(args.source_path),
            candidate_density=args.candidate_density,
            peak_pick_threshold=args.peak_pick_threshold,
            min_boundary_distance_seconds=args.min_boundary_distance_seconds,
            max_candidates=args.max_candidates,
        )
    print(f"ANALYSIS_PATH={analysis_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
