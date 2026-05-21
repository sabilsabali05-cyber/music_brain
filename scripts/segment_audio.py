from __future__ import annotations

import argparse
import json
import re
import subprocess
from hashlib import sha256
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
    try:
        return float((result.stdout or "").strip())
    except ValueError as exc:
        raise RuntimeError("Could not parse duration from ffprobe output") from exc


def checksum_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_low_energy_boundaries(
    source_path: Path, *, silence_noise_db: float = -35.0, min_silence_seconds: float = 0.6
) -> list[float]:
    command = [
        "ffmpeg",
        "-i",
        str(source_path),
        "-af",
        f"silencedetect=noise={silence_noise_db}dB:d={min_silence_seconds}",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    raw = "\n".join(part for part in [result.stdout, result.stderr] if part)
    starts = [float(v) for v in re.findall(r"silence_start:\s*([0-9.]+)", raw)]
    ends = [float(v) for v in re.findall(r"silence_end:\s*([0-9.]+)", raw)]
    count = min(len(starts), len(ends))
    boundaries: list[float] = []
    for i in range(count):
        start, end = starts[i], ends[i]
        if end > start:
            boundaries.append((start + end) / 2.0)
    return sorted(set(boundaries))


def build_fixed_core_intervals(
    *, duration_seconds: float, target_window_seconds: float, reason: str = "fixed_interval_fallback"
) -> tuple[list[tuple[float, float]], list[str], list[float]]:
    intervals: list[tuple[float, float]] = []
    reasons: list[str] = []
    confidences: list[float] = []
    core_start = 0.0
    while core_start < duration_seconds:
        core_end = min(duration_seconds, core_start + target_window_seconds)
        intervals.append((core_start, core_end))
        reasons.append(reason)
        confidences.append(0.2 if reason == "fixed_interval_fallback" else 0.1)
        core_start = core_end
    return intervals, reasons, confidences


def build_energy_core_intervals(
    *,
    duration_seconds: float,
    candidate_boundaries: list[float],
    target_window_seconds: float,
    max_window_seconds: float,
    min_segment_seconds: float,
) -> tuple[list[tuple[float, float]], list[str], list[float], int, int]:
    filtered_candidates = sorted(
        b for b in candidate_boundaries if min_segment_seconds <= b <= duration_seconds - min_segment_seconds
    )
    detected_count = len(filtered_candidates)
    accepted_count = 0

    intervals: list[tuple[float, float]] = []
    reasons: list[str] = []
    confidences: list[float] = []

    start = 0.0
    while start < duration_seconds:
        remaining = duration_seconds - start
        if remaining <= max_window_seconds:
            intervals.append((start, duration_seconds))
            reasons.append("max_window_split" if remaining > target_window_seconds else "low_energy_boundary")
            confidences.append(0.4 if remaining > target_window_seconds else 0.6)
            break

        lower = start + min_segment_seconds
        upper = min(duration_seconds, start + max_window_seconds)
        local_candidates = [b for b in filtered_candidates if lower <= b <= upper]

        if local_candidates:
            target = start + target_window_seconds
            chosen = min(local_candidates, key=lambda b: abs(b - target))
            accepted_count += 1
            end = chosen
            reason = "low_energy_boundary"
            confidence = 0.7
        else:
            end = min(duration_seconds, start + target_window_seconds)
            reason = "max_window_split" if end - start >= max_window_seconds else "uncertain_fallback"
            confidence = 0.2

        intervals.append((start, end))
        reasons.append(reason)
        confidences.append(confidence)
        start = end

    return intervals, reasons, confidences, detected_count, accepted_count


def build_manifest_graph(
    *,
    duration_seconds: float,
    core_intervals: list[tuple[float, float]],
    boundary_reasons: list[str],
    boundary_confidences: list[float],
    boundary_sources: list[str],
    feature_evidences: list[dict[str, float]],
    analysis_path: str | None,
    context_seconds: float,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    musical_segments: list[dict[str, object]] = []
    transcription_windows: list[dict[str, object]] = []
    adjacency: list[dict[str, object]] = []

    for index, (core_start, core_end) in enumerate(core_intervals):
        segment_id = f"seg_{index:04d}"
        window_id = f"win_{index:04d}"
        previous_segment_id = f"seg_{index - 1:04d}" if index > 0 else None
        next_segment_id = f"seg_{index + 1:04d}" if index < len(core_intervals) - 1 else None

        window_start = max(0.0, core_start - context_seconds)
        window_end = min(duration_seconds, core_end + context_seconds)

        musical_segments.append(
            {
                "segment_id": segment_id,
                "index": index,
                "global_start_seconds": round(core_start, 6),
                "global_end_seconds": round(core_end, 6),
                "duration_seconds": round(core_end - core_start, 6),
                "boundary_confidence": round(boundary_confidences[index], 3),
                "boundary_reason": boundary_reasons[index],
                "boundary_source": boundary_sources[index],
                "feature_evidence": feature_evidences[index],
                "analysis_path": analysis_path,
                "neighbor_context_summary": None,
                "previous_segment_id": previous_segment_id,
                "next_segment_id": next_segment_id,
                "section_label": None,
                "phrase_label": None,
                "local_summary": "Segmentation boundary candidate from current strategy.",
                "pre_context_seconds": round(min(context_seconds, core_start), 6),
                "post_context_seconds": round(min(context_seconds, duration_seconds - core_end), 6),
                "transcription_window_id": window_id,
            }
        )

        transcription_windows.append(
            {
                "window_id": window_id,
                "index": index,
                "global_start_seconds": round(window_start, 6),
                "global_end_seconds": round(window_end, 6),
                "core_start_seconds": round(core_start, 6),
                "core_end_seconds": round(core_end, 6),
                "pre_context_seconds": round(core_start - window_start, 6),
                "post_context_seconds": round(window_end - core_end, 6),
                "source_segment_ids": [segment_id],
                "chunk_audio_path": None,
                "status": "pending",
                "track_folder": None,
                "job_report": None,
                "midi_path": None,
                "error": None,
            }
        )

        if previous_segment_id is not None:
            adjacency.append(
                {
                    "from_segment_id": previous_segment_id,
                    "to_segment_id": segment_id,
                    "relation": "next",
                    "weight": 1.0,
                }
            )

    return musical_segments, transcription_windows, adjacency


def load_structure_analysis(source_path: Path) -> tuple[dict[str, object] | None, Path]:
    source_safe = safe_source_name(source_path)
    analysis_path = Path("samples") / "analysis" / source_safe / "structure_analysis.json"
    if not analysis_path.exists():
        return None, analysis_path
    payload = json.loads(analysis_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None, analysis_path
    return payload, analysis_path


def build_audio_structure_core_intervals(
    *,
    duration_seconds: float,
    boundary_candidates: list[dict[str, object]],
    target_window_seconds: float,
    max_window_seconds: float,
    min_segment_seconds: float,
    confidence_threshold: float,
) -> tuple[
    list[tuple[float, float]],
    list[str],
    list[float],
    list[str],
    list[dict[str, float]],
    int,
    int,
]:
    filtered_candidates: list[dict[str, object]] = []
    for candidate in boundary_candidates:
        if not isinstance(candidate, dict):
            continue
        time_seconds = float(candidate.get("time_seconds", -1))
        confidence = float(candidate.get("confidence", 0))
        if time_seconds < min_segment_seconds or time_seconds > duration_seconds - min_segment_seconds:
            continue
        if confidence < confidence_threshold:
            continue
        filtered_candidates.append(candidate)

    candidate_count = len(boundary_candidates)
    accepted_count = 0
    intervals: list[tuple[float, float]] = []
    reasons: list[str] = []
    confidences: list[float] = []
    sources: list[str] = []
    evidences: list[dict[str, float]] = []

    start = 0.0
    while start < duration_seconds:
        remaining = duration_seconds - start
        if remaining <= max_window_seconds:
            intervals.append((start, duration_seconds))
            reasons.append("combined_audio_novelty")
            confidences.append(0.6 if accepted_count > 0 else 0.2)
            sources.append("audio_structure_v1" if accepted_count > 0 else "fixed")
            evidences.append({})
            break

        lower = start + min_segment_seconds
        upper = min(duration_seconds, start + max_window_seconds)
        local_candidates = [
            c for c in filtered_candidates if lower <= float(c.get("time_seconds", -1)) <= upper
        ]
        if local_candidates:
            target = start + target_window_seconds
            chosen = max(
                local_candidates,
                key=lambda c: float(c.get("confidence", 0))
                - (abs(float(c.get("time_seconds", 0)) - target) / max(1.0, target_window_seconds)),
            )
            end = float(chosen.get("time_seconds"))
            accepted_count += 1
            reason = str(chosen.get("reason", "combined_audio_novelty"))
            confidence = float(chosen.get("confidence", 0.6))
            evidence = chosen.get("feature_evidence", {})
            intervals.append((start, end))
            reasons.append(reason)
            confidences.append(confidence)
            sources.append("audio_structure_v1")
            evidences.append(evidence if isinstance(evidence, dict) else {})
            start = end
            continue

        end = min(duration_seconds, start + target_window_seconds)
        intervals.append((start, end))
        reasons.append("fixed_interval_fallback")
        confidences.append(0.2)
        sources.append("fixed")
        evidences.append({})
        start = end

    normalized_evidences: list[dict[str, float]] = []
    for evidence in evidences:
        if not isinstance(evidence, dict):
            normalized_evidences.append({})
            continue
        normalized = {}
        for key in ["energy_change", "onset_change", "chroma_change", "timbre_change", "combined_novelty"]:
            value = evidence.get(key, 0.0)
            try:
                normalized[key] = round(float(value), 6)
            except Exception:
                normalized[key] = 0.0
        normalized_evidences.append(normalized)

    return intervals, reasons, confidences, sources, normalized_evidences, candidate_count, accepted_count


def extract_window_audio(source_path: Path, output_path: Path, start: float, end: float) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.0, end - start)
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start}",
        "-t",
        f"{duration}",
        "-i",
        str(source_path),
        "-vn",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed extracting window: {(result.stderr or '').strip()}")


def segment_audio(
    source_path: Path,
    *,
    strategy: str,
    target_window_seconds: float,
    max_window_seconds: float,
    context_seconds: float,
) -> Path:
    if not source_path.exists():
        raise FileNotFoundError(f"Audio file does not exist: {source_path}")
    if target_window_seconds <= 0:
        raise ValueError("target_window_seconds must be > 0")
    if max_window_seconds < target_window_seconds:
        raise ValueError("max_window_seconds must be >= target_window_seconds")

    duration_seconds = probe_duration_seconds(source_path)
    source_name_safe = safe_source_name(source_path)
    source_root = Path("samples") / "segments" / source_name_safe
    source_root.mkdir(parents=True, exist_ok=True)

    segmentation_diagnostics: dict[str, object] = {
        "algorithm_version": "segmentation_v2",
        "detected_boundary_count": 0,
        "candidate_boundary_count": 0,
        "accepted_boundary_count": 0,
        "rejected_boundary_count": 0,
        "available_features": [],
        "missing_features": [],
        "analysis_path": None,
        "analysis_backend": None,
        "analysis_version": None,
        "fallback_used": False,
        "notes": "",
    }

    manifest_strategy = "fixed_with_context"
    boundary_sources: list[str] = []
    feature_evidences: list[dict[str, float]] = []
    analysis_path_value: str | None = None
    if strategy == "fixed":
        intervals, reasons, confidences = build_fixed_core_intervals(
            duration_seconds=duration_seconds,
            target_window_seconds=target_window_seconds,
            reason="fixed_interval_fallback",
        )
        boundary_sources = ["fixed"] * len(intervals)
        feature_evidences = [{} for _ in intervals]
        segmentation_diagnostics["notes"] = "Fixed baseline segmentation."
        segmentation_diagnostics["candidate_boundary_count"] = 0
    else:
        if strategy == "audio_structure":
            analysis_payload, analysis_path = load_structure_analysis(source_path)
            if analysis_payload is None:
                try:
                    from scripts.analyze_audio_structure import analyze_audio_structure

                    generated_path = analyze_audio_structure(source_path)
                    analysis_payload, analysis_path = load_structure_analysis(source_path)
                    analysis_path_value = generated_path.as_posix()
                except Exception as exc:
                    segmentation_diagnostics["notes"] = (
                        "Audio structure analysis unavailable; used fixed interval fallback with context. "
                        f"analysis_error={exc}"
                    )
                    analysis_payload = None
            if analysis_payload is not None:
                analysis_path_value = analysis_path.resolve().as_posix()
                diagnostics = analysis_payload.get("diagnostics", {})
                boundary_candidates = analysis_payload.get("boundary_candidates", [])
                if not isinstance(diagnostics, dict):
                    diagnostics = {}
                if not isinstance(boundary_candidates, list):
                    boundary_candidates = []
                min_segment_seconds = max(10.0, target_window_seconds * 0.5)
                (
                    intervals,
                    reasons,
                    confidences,
                    boundary_sources,
                    feature_evidences,
                    candidate_count,
                    accepted,
                ) = build_audio_structure_core_intervals(
                    duration_seconds=duration_seconds,
                    boundary_candidates=boundary_candidates,
                    target_window_seconds=target_window_seconds,
                    max_window_seconds=max_window_seconds,
                    min_segment_seconds=min_segment_seconds,
                    confidence_threshold=0.55,
                )
                available_features = diagnostics.get("available_features", [])
                missing_features = diagnostics.get("missing_features", [])
                segmentation_diagnostics["analysis_path"] = analysis_path_value
                segmentation_diagnostics["analysis_backend"] = analysis_payload.get("analysis_backend")
                segmentation_diagnostics["analysis_version"] = analysis_payload.get("analysis_version")
                segmentation_diagnostics["candidate_boundary_count"] = candidate_count
                segmentation_diagnostics["detected_boundary_count"] = candidate_count
                segmentation_diagnostics["accepted_boundary_count"] = accepted
                segmentation_diagnostics["rejected_boundary_count"] = max(0, candidate_count - accepted)
                segmentation_diagnostics["available_features"] = (
                    available_features if isinstance(available_features, list) else []
                )
                segmentation_diagnostics["missing_features"] = (
                    missing_features if isinstance(missing_features, list) else []
                )
                if accepted == 0:
                    intervals, reasons, confidences = build_fixed_core_intervals(
                        duration_seconds=duration_seconds,
                        target_window_seconds=target_window_seconds,
                        reason="uncertain_audio_structure_fallback",
                    )
                    boundary_sources = ["fixed"] * len(intervals)
                    feature_evidences = [{} for _ in intervals]
                    segmentation_diagnostics["fallback_used"] = True
                    segmentation_diagnostics["notes"] = (
                        "Audio-structure boundary candidates were too weak; used fixed interval fallback with context."
                    )
                    manifest_strategy = "fixed_with_context"
                else:
                    manifest_strategy = "audio_structure_v1"
                    segmentation_diagnostics["notes"] = "Audio structure boundary candidates accepted conservatively."
            else:
                intervals, reasons, confidences = build_fixed_core_intervals(
                    duration_seconds=duration_seconds,
                    target_window_seconds=target_window_seconds,
                    reason="uncertain_audio_structure_fallback",
                )
                boundary_sources = ["fixed"] * len(intervals)
                feature_evidences = [{} for _ in intervals]
                segmentation_diagnostics["fallback_used"] = True
                manifest_strategy = "fixed_with_context"
                segmentation_diagnostics["candidate_boundary_count"] = 0
                segmentation_diagnostics["detected_boundary_count"] = 0
                segmentation_diagnostics["accepted_boundary_count"] = 0
                segmentation_diagnostics["rejected_boundary_count"] = 0
                segmentation_diagnostics["analysis_path"] = analysis_path_value
                if not segmentation_diagnostics["notes"]:
                    segmentation_diagnostics["notes"] = (
                        "Audio structure analysis missing; used fixed interval fallback with context."
                    )
        else:
            candidates = detect_low_energy_boundaries(source_path)
            min_segment_seconds = max(10.0, target_window_seconds * 0.5)
            intervals, reasons, confidences, detected, accepted = build_energy_core_intervals(
                duration_seconds=duration_seconds,
                candidate_boundaries=candidates,
                target_window_seconds=target_window_seconds,
                max_window_seconds=max_window_seconds,
                min_segment_seconds=min_segment_seconds,
            )
            boundary_sources = ["energy_v1"] * len(intervals)
            feature_evidences = [{} for _ in intervals]
            segmentation_diagnostics["detected_boundary_count"] = detected
            segmentation_diagnostics["candidate_boundary_count"] = detected
            segmentation_diagnostics["accepted_boundary_count"] = accepted
            segmentation_diagnostics["rejected_boundary_count"] = max(0, detected - accepted)
            segmentation_diagnostics["available_features"] = ["silence_gaps"]
            segmentation_diagnostics["missing_features"] = ["onset_strength", "chroma_change", "timbre_change"]

            if accepted == 0:
                intervals, reasons, confidences = build_fixed_core_intervals(
                    duration_seconds=duration_seconds,
                    target_window_seconds=target_window_seconds,
                    reason="uncertain_fallback",
                )
                boundary_sources = ["fixed"] * len(intervals)
                feature_evidences = [{} for _ in intervals]
                segmentation_diagnostics["fallback_used"] = True
                segmentation_diagnostics["notes"] = (
                    "Energy boundary detector did not produce confident boundaries; "
                    "used fixed interval fallback with context."
                )
                manifest_strategy = "fixed_with_context"
            else:
                manifest_strategy = (
                    "energy_v1" if strategy == "energy" else "hybrid_scaffold_with_energy_boundaries"
                )
                segmentation_diagnostics["notes"] = "Energy boundary candidates accepted conservatively."

    fallback_used = bool(segmentation_diagnostics.get("fallback_used"))
    strategy_requested = strategy
    strategy_used = manifest_strategy

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    strategy_slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", strategy_used)
    run_id = f"{timestamp}_{strategy_slug}"
    run_root = source_root / run_id
    windows_root = run_root / "windows"
    run_root.mkdir(parents=True, exist_ok=True)

    musical_segments, transcription_windows, adjacency = build_manifest_graph(
        duration_seconds=duration_seconds,
        core_intervals=intervals,
        boundary_reasons=reasons,
        boundary_confidences=confidences,
        boundary_sources=boundary_sources,
        feature_evidences=feature_evidences,
        analysis_path=analysis_path_value,
        context_seconds=context_seconds,
    )

    for window in transcription_windows:
        window_index = int(window["index"])
        chunk_path = windows_root / f"window_{window_index:04d}.wav"
        extract_window_audio(
            source_path=source_path,
            output_path=chunk_path,
            start=float(window["global_start_seconds"]),
            end=float(window["global_end_seconds"]),
        )
        window["chunk_audio_path"] = chunk_path.resolve().as_posix()

    source_stat = source_path.stat()
    manifest = {
        "performance_id": f"perf_{source_name_safe}",
        "source_path": source_path.resolve().as_posix(),
        "source_name": source_path.name,
        "source_audio_sha256": checksum_sha256(source_path),
        "source_audio_size_bytes": int(source_stat.st_size),
        "source_audio_modified_time": datetime.fromtimestamp(
            source_stat.st_mtime, tz=timezone.utc
        ).isoformat(),
        "duration_seconds": round(duration_seconds, 6),
        "segmentation_strategy": strategy_used,
        "strategy_requested": strategy_requested,
        "strategy_used": strategy_used,
        "fallback_used": fallback_used,
        "segmentation_run_id": run_id,
        "segmentation_run_dir": run_root.resolve().as_posix(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "segmentation_diagnostics": segmentation_diagnostics,
        "musical_segments": musical_segments,
        "transcription_windows": transcription_windows,
        "context_graph": {"adjacency": adjacency},
    }

    manifest_path = run_root / "segments_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    latest_pointer = source_root / "latest_manifest.txt"
    latest_pointer.write_text(manifest_path.resolve().as_posix(), encoding="utf-8")
    return manifest_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create segmentation manifest and context-padded windows.")
    parser.add_argument("source_path", help="Path to input performance audio.")
    parser.add_argument("--strategy", choices=["fixed", "energy", "hybrid", "audio_structure"], default="hybrid")
    parser.add_argument("--target-window-seconds", type=float, default=60.0)
    parser.add_argument("--max-window-seconds", type=float, default=90.0)
    parser.add_argument("--context-seconds", type=float, default=5.0)
    args = parser.parse_args()

    manifest_path = segment_audio(
        Path(args.source_path),
        strategy=args.strategy,
        target_window_seconds=args.target_window_seconds,
        max_window_seconds=args.max_window_seconds,
        context_seconds=args.context_seconds,
    )
    print(f"MANIFEST_PATH={manifest_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
