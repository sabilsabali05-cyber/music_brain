from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _safe_slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("_") or "unknown"


def _feature_summary(feature_evidence: object) -> str:
    if not isinstance(feature_evidence, dict) or not feature_evidence:
        return "-"
    keys = ["combined_novelty", "chroma_change", "timbre_change", "onset_change", "energy_change"]
    chunks: list[str] = []
    for key in keys:
        if key not in feature_evidence:
            continue
        try:
            chunks.append(f"{key}={float(feature_evidence[key]):.3f}")
        except Exception:
            chunks.append(f"{key}={feature_evidence[key]}")
    return ", ".join(chunks) if chunks else "-"


def _load_analysis_candidates(analysis_path: str | None) -> tuple[list[dict[str, object]], float]:
    if not analysis_path:
        return [], 0.5
    path = Path(analysis_path)
    if not path.exists():
        return [], 0.5
    payload = json.loads(path.read_text(encoding="utf-8"))
    frame_hop = 0.5
    if isinstance(payload, dict):
        try:
            frame_hop = max(0.05, float(payload.get("frame_hop_seconds", 0.5)))
        except Exception:
            frame_hop = 0.5
        candidates = payload.get("boundary_candidates", [])
        if isinstance(candidates, list):
            return [c for c in candidates if isinstance(c, dict)], frame_hop
    return [], frame_hop


def _matched_candidate_times(manifest: dict[str, object]) -> list[float]:
    duration = float(manifest.get("duration_seconds", 0.0) or 0.0)
    segments = manifest.get("musical_segments", [])
    if not isinstance(segments, list):
        return []
    values: list[float] = []
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        if str(seg.get("boundary_source")) != "audio_structure_v1":
            continue
        try:
            end_time = float(seg.get("global_end_seconds", 0.0))
        except Exception:
            continue
        if abs(end_time - duration) < 1e-6:
            continue
        values.append(end_time)
    return values


def build_review_report(manifest: dict[str, object], manifest_path: Path) -> str:
    source_name = str(manifest.get("source_name", manifest_path.stem))
    duration = manifest.get("duration_seconds")
    strategy_requested = manifest.get("strategy_requested")
    strategy_used = manifest.get("strategy_used", manifest.get("segmentation_strategy"))
    fallback_used = manifest.get("fallback_used")
    run_id = str(manifest.get("segmentation_run_id", manifest_path.parent.name))
    diagnostics = manifest.get("segmentation_diagnostics", {})
    if not isinstance(diagnostics, dict):
        diagnostics = {}

    available_features = diagnostics.get("available_features", [])
    missing_features = diagnostics.get("missing_features", [])
    candidate_boundary_count = diagnostics.get("candidate_boundary_count")
    accepted_boundary_count = diagnostics.get("accepted_boundary_count")
    analysis_path = diagnostics.get("analysis_path")

    lines: list[str] = []
    lines.append(f"# Segmentation Review: {source_name}")
    lines.append("")
    lines.append(f"- manifest_path: `{manifest_path.resolve().as_posix()}`")
    lines.append(f"- run_id: `{run_id}`")
    lines.append(f"- source_name: `{source_name}`")
    lines.append(f"- duration_seconds: `{duration}`")
    lines.append(f"- strategy_requested: `{strategy_requested}`")
    lines.append(f"- strategy_used: `{strategy_used}`")
    lines.append(f"- fallback_used: `{fallback_used}`")
    lines.append(f"- available_features: `{available_features}`")
    lines.append(f"- missing_features: `{missing_features}`")
    lines.append(f"- candidate_boundary_count: `{candidate_boundary_count}`")
    lines.append(f"- accepted_boundary_count: `{accepted_boundary_count}`")
    lines.append(f"- analysis_path: `{analysis_path}`")
    lines.append("")

    lines.append("## Accepted Musical Segments")
    lines.append("")
    lines.append("| index | start | end | duration | confidence | reason | evidence | prev | next | window |")
    lines.append("|---|---:|---:|---:|---:|---|---|---|---|---|")
    segments = manifest.get("musical_segments", [])
    if isinstance(segments, list):
        for seg in segments:
            if not isinstance(seg, dict):
                continue
            lines.append(
                f"| {seg.get('index')} | {seg.get('global_start_seconds')} | {seg.get('global_end_seconds')} | "
                f"{seg.get('duration_seconds')} | {seg.get('boundary_confidence')} | {seg.get('boundary_reason')} | "
                f"{_feature_summary(seg.get('feature_evidence'))} | {seg.get('previous_segment_id')} | "
                f"{seg.get('next_segment_id')} | {seg.get('transcription_window_id')} |"
            )
    lines.append("")

    lines.append("## Candidate Boundaries (Accepted vs Rejected)")
    lines.append("")
    lines.append("| time_seconds | confidence | reason | status | evidence |")
    lines.append("|---:|---:|---|---|---|")
    candidates, tolerance = _load_analysis_candidates(str(analysis_path) if analysis_path else None)
    matched = _matched_candidate_times(manifest)
    for candidate in candidates:
        try:
            time_seconds = float(candidate.get("time_seconds", 0.0))
        except Exception:
            time_seconds = 0.0
        status = "accepted" if any(abs(time_seconds - t) <= tolerance for t in matched) else "rejected_or_unused"
        lines.append(
            f"| {time_seconds:.3f} | {candidate.get('confidence')} | {candidate.get('reason')} | "
            f"{status} | {_feature_summary(candidate.get('feature_evidence'))} |"
        )
    if not candidates:
        lines.append("| - | - | - | unavailable | analysis boundary candidates not available |")
    lines.append("")

    lines.append("## Transcription Windows")
    lines.append("")
    lines.append("| index | global_start | global_end | core_start | core_end | context_pre | context_post | source_segment_ids | status |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---|---|")
    windows = manifest.get("transcription_windows", [])
    if isinstance(windows, list):
        for window in windows:
            if not isinstance(window, dict):
                continue
            lines.append(
                f"| {window.get('index')} | {window.get('global_start_seconds')} | {window.get('global_end_seconds')} | "
                f"{window.get('core_start_seconds')} | {window.get('core_end_seconds')} | "
                f"{window.get('pre_context_seconds')} | {window.get('post_context_seconds')} | "
                f"{window.get('source_segment_ids')} | {window.get('status')} |"
            )
    lines.append("")

    lines.append("## Review Questions")
    lines.append("")
    lines.append("- Do these boundaries match musical phrases?")
    lines.append("- Are segments too long or too short?")
    lines.append("- Should threshold be stricter or looser?")
    lines.append("- Should beat/bar snapping be added?")
    lines.append("- Should chroma/timbre be weighted more?")
    lines.append("")
    return "\n".join(lines)


def review_segments(manifest_path: Path) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_name = str(manifest.get("source_name", manifest_path.stem))
    source_slug = _safe_slug(Path(source_name).stem)
    run_id = _safe_slug(str(manifest.get("segmentation_run_id", manifest_path.parent.name)))
    output_dir = Path("reports") / "segment_reviews"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{source_slug}_{run_id}.md"
    report_text = build_review_report(manifest, manifest_path)
    output_path.write_text(report_text, encoding="utf-8")
    return output_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a human-readable segmentation quality review report.")
    parser.add_argument("manifest_path", help="Path to segments_manifest.json")
    args = parser.parse_args()
    output_path = review_segments(Path(args.manifest_path))
    print(f"REVIEW_REPORT_PATH={output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
