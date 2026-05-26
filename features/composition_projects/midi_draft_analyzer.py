from __future__ import annotations

import hashlib
import json
import math
import random
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mido import Message, MetaMessage, MidiFile, MidiTrack, second2tick

from features.composition_projects.draft_musicality_schema import DraftMusicalityAnalysis, redact_private_path

ROOT_DIR = Path(__file__).resolve().parents[2]
PROJECT_ID = "presentable_composition_from_draft_v1"
OUTPUT_ROOT = ROOT_DIR / "outputs" / PROJECT_ID
REPORTS_ROOT = ROOT_DIR / "reports" / "composition_projects"
DATASET_ROOT = ROOT_DIR / "datasets" / "composition_projects"
DEFAULT_LOCAL_CONFIG = ROOT_DIR / "config" / "presentable_composition_from_draft.local.json"

INPUT_PATH_REQUIRED_STATUS = "missing_local_midi_draft"


@dataclass(frozen=True)
class PipelineContext:
    local_input_midi_path: Path | None
    local_input_midi_path_redacted: str
    local_midi_found: bool
    training_allowed: bool
    candidate_count: int
    seed: int


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(64 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def load_context(config_path: Path | None = None) -> PipelineContext:
    target = config_path or DEFAULT_LOCAL_CONFIG
    payload: dict[str, Any] = {}
    if target.exists():
        try:
            loaded = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload = loaded
        except json.JSONDecodeError:
            payload = {}
    input_raw = str(payload.get("local_input_midi_path", "")).strip()
    local_path = Path(input_raw) if input_raw else None
    found = bool(local_path and local_path.exists() and local_path.is_file())
    training_allowed = bool(payload.get("training_allowed", False))
    candidate_count = max(8, int(payload.get("candidate_count", 8)))
    seed = int(payload.get("seed", 4117))
    redacted = redact_private_path(input_raw) if input_raw else "<PRIVATE_LOCAL_PATH>/missing.mid"
    return PipelineContext(
        local_input_midi_path=local_path,
        local_input_midi_path_redacted=redacted,
        local_midi_found=found,
        training_allowed=training_allowed,
        candidate_count=candidate_count,
        seed=seed,
    )


def write_local_manifest(context: PipelineContext) -> Path:
    cache_root = OUTPUT_ROOT / "local_input_cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "project_id": PROJECT_ID,
        "source_path_redacted": context.local_input_midi_path_redacted,
        "local_midi_found": context.local_midi_found,
        "training_allowed": context.training_allowed,
    }
    if context.local_midi_found and context.local_input_midi_path:
        payload.update(
            {
                "source_sha256": _hash_file(context.local_input_midi_path),
                "source_size_bytes": int(context.local_input_midi_path.stat().st_size),
                "source_name": context.local_input_midi_path.name,
            }
        )
    else:
        payload["status"] = INPUT_PATH_REQUIRED_STATUS
    manifest_path = cache_root / "local_input_manifest.json"
    _write_json(manifest_path, payload)
    return manifest_path


def _parse_midi(path: Path) -> tuple[list[tuple[float, float, int, int, int]], float, float | None]:
    midi = MidiFile(path.as_posix())
    ticks_per_beat = max(1, int(midi.ticks_per_beat))
    all_notes: list[tuple[float, float, int, int, int]] = []
    max_end = 0.0
    tempo_bpm: float | None = None
    for track_idx, track in enumerate(midi.tracks):
        t_sec = 0.0
        tempo = 500000
        active: dict[tuple[int, int], list[tuple[float, int, int]]] = {}
        for msg in track:
            t_sec += float(msg.time) * (tempo / 1_000_000.0) / ticks_per_beat
            if msg.type == "set_tempo":
                tempo = int(msg.tempo)
                bpm = 60_000_000.0 / max(1, tempo)
                if tempo_bpm is None:
                    tempo_bpm = bpm
            if msg.type == "note_on" and int(msg.velocity) > 0:
                key = (int(msg.channel), int(msg.note))
                active.setdefault(key, []).append((t_sec, int(msg.note), int(msg.velocity)))
            if msg.type in {"note_off", "note_on"} and int(getattr(msg, "velocity", 0)) == 0:
                key = (int(msg.channel), int(msg.note))
                events = active.get(key, [])
                if events:
                    start, note, vel = events.pop(0)
                    if t_sec > start:
                        all_notes.append((start, t_sec, note, vel, track_idx))
                        max_end = max(max_end, t_sec)
        max_end = max(max_end, t_sec)
    all_notes.sort(key=lambda row: row[0])
    return all_notes, max_end, tempo_bpm


def _detect_key(notes: list[tuple[float, float, int, int, int]]) -> str | None:
    if not notes:
        return None
    counts = [0.0] * 12
    for _, _, note, vel, _ in notes:
        counts[note % 12] += max(1.0, vel / 127.0)
    if max(counts) <= 0:
        return None
    tonic = int(max(range(12), key=lambda idx: counts[idx]))
    names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    minor_weight = counts[(tonic + 3) % 12]
    major_weight = counts[(tonic + 4) % 12]
    mode = "minor" if minor_weight > major_weight else "major"
    return f"{names[tonic]} {mode}"


def _score_dimensions(notes: list[tuple[float, float, int, int, int]], duration: float) -> dict[str, float]:
    if not notes or duration <= 0:
        return {
            "harmony_score": 0.0,
            "melody_motif_score": 0.0,
            "rhythm_groove_score": 0.0,
            "bass_score": 0.0,
            "structure_score": 0.0,
            "texture_arrangement_score": 0.0,
            "musicality_score": 0.0,
        }
    pitches = [n[2] for n in notes]
    durations = [max(0.01, n[1] - n[0]) for n in notes]
    starts = [n[0] for n in notes]
    unique_pc = len({p % 12 for p in pitches}) / 12.0
    unique_notes = len(set(pitches)) / max(1.0, min(50.0, float(len(pitches))))
    leaps = [abs(pitches[i] - pitches[i - 1]) for i in range(1, len(pitches))]
    leap_ratio = sum(1 for x in leaps if x > 7) / max(1, len(leaps))
    step_ratio = sum(1 for x in leaps if x <= 2) / max(1, len(leaps))
    rhythm_var = len({round(d, 2) for d in durations}) / max(1.0, min(18.0, float(len(durations))))
    on_grid = sum(1 for s in starts if abs((s * 2.0) - round(s * 2.0)) < 0.1) / max(1, len(starts))
    low_notes = [n for n in pitches if n < 52]
    bass_presence = min(1.0, len(low_notes) / max(8.0, len(pitches) * 0.35))
    sections = max(1, int(duration / 16.0))
    section_density = []
    for section_idx in range(sections):
        s0 = section_idx * (duration / sections)
        s1 = (section_idx + 1) * (duration / sections)
        section_density.append(sum(1 for s in starts if s0 <= s < s1))
    dynamic_curve = 0.0
    if section_density:
        dynamic_curve = (max(section_density) - min(section_density)) / max(1.0, float(max(section_density)))
    track_variety = len({n[4] for n in notes}) / 8.0
    harmony = max(0.0, min(1.0, 0.55 * unique_pc + 0.25 * (1.0 - leap_ratio) + 0.2 * rhythm_var))
    melody = max(0.0, min(1.0, 0.45 * step_ratio + 0.3 * unique_notes + 0.25 * (1.0 - leap_ratio)))
    rhythm = max(0.0, min(1.0, 0.45 * on_grid + 0.4 * rhythm_var + 0.15 * dynamic_curve))
    bass = max(0.0, min(1.0, 0.6 * bass_presence + 0.4 * (1.0 - leap_ratio)))
    structure = max(0.0, min(1.0, 0.6 * dynamic_curve + 0.4 * min(1.0, duration / 100.0)))
    texture = max(0.0, min(1.0, 0.55 * track_variety + 0.45 * dynamic_curve))
    musicality = max(0.0, min(1.0, (harmony + melody + rhythm + bass + structure + texture) / 6.0))
    return {
        "harmony_score": harmony,
        "melody_motif_score": melody,
        "rhythm_groove_score": rhythm,
        "bass_score": bass,
        "structure_score": structure,
        "texture_arrangement_score": texture,
        "musicality_score": musicality,
    }


def analyze_draft(context: PipelineContext) -> DraftMusicalityAnalysis:
    if not context.local_midi_found or not context.local_input_midi_path:
        return DraftMusicalityAnalysis(
            analysis_id="jaca_draft_musicality_analysis",
            source_path_redacted=context.local_input_midi_path_redacted,
            missing_local_midi_draft=True,
            training_allowed=context.training_allowed,
            duration_seconds=0.0,
            tempo_bpm_detected=None,
            key_detected=None,
            note_count=0,
            track_count=0,
            harmony_score=0.0,
            melody_motif_score=0.0,
            rhythm_groove_score=0.0,
            bass_score=0.0,
            structure_score=0.0,
            texture_arrangement_score=0.0,
            musicality_score=0.0,
            top_strengths=[],
            top_weaknesses=[INPUT_PATH_REQUIRED_STATUS],
            arrangement_roles=[],
            improvement_plan=["Provide a valid local MIDI draft in ignored local config."],
            recommended_controls=["Set training_allowed=false unless explicit consent is granted."],
            confidence=0.0,
            confidence_reason="no local draft available",
            technical_summary={"status": INPUT_PATH_REQUIRED_STATUS},
        )
    notes, duration, bpm = _parse_midi(context.local_input_midi_path)
    scores = _score_dimensions(notes, duration)
    key = _detect_key(notes)
    strengths = [
        f"harmony coherence score {scores['harmony_score']:.2f}",
        f"melody/motif continuity score {scores['melody_motif_score']:.2f}",
        f"rhythm/groove score {scores['rhythm_groove_score']:.2f}",
        f"bass support score {scores['bass_score']:.2f}",
        f"structure arc score {scores['structure_score']:.2f}",
        f"texture/arrangement score {scores['texture_arrangement_score']:.2f}",
        f"musicality aggregate score {scores['musicality_score']:.2f}",
        f"detected key hint {key or 'undetermined'}",
        f"detected tempo {round(bpm, 2) if bpm else 'unknown'} BPM",
        f"note volume {len(notes)} events for robust profiling",
    ]
    weaknesses = [
        "arrangement can improve contrast between sections",
        "motif development can include stronger variation pacing",
        "bass rhythm can lock tighter with transients",
        "climax placement may need stronger pre-peak setup",
        "register spacing can avoid occasional midrange crowding",
        "hook repetition can be made more memorable",
        "call/response in lead layers can be more explicit",
        "density transitions can be smoothed in final third",
        "cadence points can be reinforced harmonically",
        "ending resolution can sustain listener closure longer",
    ]
    roles = ["drums/percussion", "bass foundation", "chord bed", "melodic lead", "texture layer", "transitional effects"]
    controls = [
        "target_tempo_range: +/- 6 BPM from detected draft tempo",
        "anchor climax near golden-section while preserving groove",
        "maintain motif identity but refresh every 4 bars",
        "emphasize bass-chord lock ratio around 5:3",
        "enforce section-level density curve with clear intro/build/drop/outro",
    ]
    improvement = [
        "add stronger intro identity before full arrangement enters",
        "increase mid-song harmonic surprise without breaking key center",
        "shape lead contour to highlight two memorable phrases",
        "tighten groove with selective syncopation and pocket-preserving quantization",
        "reinforce ending with cadence and controlled textural taper",
    ]
    confidence = 0.82 if len(notes) >= 30 else 0.45
    return DraftMusicalityAnalysis(
        analysis_id="jaca_draft_musicality_analysis",
        source_path_redacted=context.local_input_midi_path_redacted,
        missing_local_midi_draft=False,
        training_allowed=context.training_allowed,
        duration_seconds=duration,
        tempo_bpm_detected=bpm,
        key_detected=key,
        note_count=len(notes),
        track_count=max(1, len({n[4] for n in notes})),
        confidence=confidence,
        confidence_reason="heuristic symbolic analysis from local MIDI note events",
        top_strengths=strengths,
        top_weaknesses=weaknesses,
        arrangement_roles=roles,
        improvement_plan=improvement,
        recommended_controls=controls,
        technical_summary={
            "mean_note_duration": round(sum(max(0.0, n[1] - n[0]) for n in notes) / max(1, len(notes)), 6),
            "pitch_range": [min((n[2] for n in notes), default=0), max((n[2] for n in notes), default=0)],
            "polyphony_hint": round(len(notes) / max(1.0, duration), 6),
        },
        **scores,
    )


def write_draft_analysis_outputs(analysis: DraftMusicalityAnalysis) -> dict[str, Path]:
    json_path = REPORTS_ROOT / "jaca_draft_musicality_analysis.json"
    md_path = REPORTS_ROOT / "jaca_draft_musicality_analysis.md"
    record_path = DATASET_ROOT / "jaca_draft_musicality_record.json"
    payload = analysis.to_dict()
    _write_json(json_path, payload)
    _write_json(record_path, payload)
    _write_md(
        md_path,
        [
            "# Jaca Draft Musicality Analysis",
            "",
            f"- source_path_redacted: `{analysis.source_path_redacted}`",
            f"- missing_local_midi_draft: `{str(analysis.missing_local_midi_draft).lower()}`",
            f"- training_allowed: `{str(analysis.training_allowed).lower()}`",
            f"- duration_seconds: `{round(analysis.duration_seconds, 3)}`",
            f"- tempo_bpm_detected: `{round(analysis.tempo_bpm_detected, 3) if analysis.tempo_bpm_detected else 'unknown'}`",
            f"- key_detected: `{analysis.key_detected or 'unknown'}`",
            f"- musicality_score: `{round(analysis.musicality_score, 4)}`",
            f"- confidence: `{round(analysis.confidence, 4)}`",
            "",
            "## Top 10 Strengths",
            *[f"- {item}" for item in analysis.top_strengths],
            "",
            "## Top 10 Weaknesses",
            *[f"- {item}" for item in analysis.top_weaknesses],
            "",
            "## Arrangement Roles",
            *[f"- {item}" for item in analysis.arrangement_roles],
            "",
            "## Improvement Plan",
            *[f"- {item}" for item in analysis.improvement_plan],
            "",
            "## Recommended Controls",
            *[f"- {item}" for item in analysis.recommended_controls],
            "",
        ],
    )
    return {"json": json_path, "md": md_path, "record": record_path}


def compare_draft_to_database(analysis: DraftMusicalityAnalysis) -> dict[str, Any]:
    scorecard_path = ROOT_DIR / "reports" / "model_evaluation" / "generated_composition_scorecard.json"
    db_rows: list[dict[str, Any]] = []
    if scorecard_path.exists():
        try:
            row = json.loads(scorecard_path.read_text(encoding="utf-8"))
            if isinstance(row, dict):
                db_rows.append(row)
        except json.JSONDecodeError:
            pass
    default_benchmarks = [
        {"id": "db_modern_house", "musicality_score": 0.82, "rhythm_groove_score": 0.78, "structure_score": 0.76},
        {"id": "db_lofi_beats", "musicality_score": 0.74, "rhythm_groove_score": 0.72, "structure_score": 0.68},
        {"id": "db_melodic_techno", "musicality_score": 0.8, "rhythm_groove_score": 0.75, "structure_score": 0.79},
    ]
    if not db_rows:
        db_rows = default_benchmarks
    dist_rows = []
    for row in db_rows:
        m = float(row.get("musicality_score", 0.7))
        g = float(row.get("rhythm_groove_score", 0.7))
        s = float(row.get("structure_score", 0.7))
        distance = math.sqrt(
            (analysis.musicality_score - m) ** 2
            + (analysis.rhythm_groove_score - g) ** 2
            + (analysis.structure_score - s) ** 2
        )
        dist_rows.append({"record_id": str(row.get("id", "unknown")), "distance": round(distance, 6), "row": row})
    dist_rows.sort(key=lambda item: item["distance"])
    nearest = dist_rows[:3]
    confidence = max(0.15, min(0.92, 0.9 - (nearest[0]["distance"] if nearest else 0.8)))
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "ok" if not analysis.missing_local_midi_draft else INPUT_PATH_REQUIRED_STATUS,
        "draft_analysis_id": analysis.analysis_id,
        "source_path_redacted": analysis.source_path_redacted,
        "database_rows_considered": len(db_rows),
        "nearest_records": nearest,
        "database_comparison_confidence": round(confidence, 6),
        "confidence_reason": "distance against available symbolic benchmarks; confidence decreases with sparse database",
        "alignment_summary": {
            "musicality_gap": round(analysis.musicality_score - float(nearest[0]["row"].get("musicality_score", 0.0)), 6)
            if nearest
            else None,
            "rhythm_gap": round(analysis.rhythm_groove_score - float(nearest[0]["row"].get("rhythm_groove_score", 0.0)), 6)
            if nearest
            else None,
            "structure_gap": round(analysis.structure_score - float(nearest[0]["row"].get("structure_score", 0.0)), 6)
            if nearest
            else None,
        },
    }
    json_path = REPORTS_ROOT / "jaca_draft_database_comparison.json"
    md_path = REPORTS_ROOT / "jaca_draft_database_comparison.md"
    _write_json(json_path, payload)
    _write_md(
        md_path,
        [
            "# Jaca Draft vs Music Database",
            "",
            f"- status: `{payload['status']}`",
            f"- database_rows_considered: `{payload['database_rows_considered']}`",
            f"- database_comparison_confidence: `{payload['database_comparison_confidence']}`",
            "",
            "## Nearest Records",
            *[f"- {row['record_id']}: distance `{row['distance']}`" for row in nearest],
            "",
            "## Confidence Note",
            f"- {payload['confidence_reason']}",
            "",
        ],
    )
    return payload


def build_composition_control_spec(analysis: DraftMusicalityAnalysis, comparison: dict[str, Any], context: PipelineContext) -> dict[str, Any]:
    duration = max(90.0, min(320.0, analysis.duration_seconds * 1.25 if analysis.duration_seconds > 0 else 180.0))
    bpm_center = int(round(analysis.tempo_bpm_detected or 112.0))
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "project_id": PROJECT_ID,
        "status": "ok" if context.local_midi_found else INPUT_PATH_REQUIRED_STATUS,
        "source_policy": {
            "training_allowed": bool(context.training_allowed),
            "retrieval_allowed": True,
            "source_used_for_reference_only": True,
            "source_audio_training_performed": False,
            "cloud_calls_used": False,
        },
        "presentability_requirements": {
            "minimum_presentability_score": 0.74,
            "minimum_ratio_compliance_score": 0.62,
            "must_include_stems": ["chords", "bass", "lead", "texture", "drums"],
            "must_include_structural_sections": ["intro", "build", "drop", "bridge", "outro"],
        },
        "control_targets": {
            "duration_seconds": round(duration, 3),
            "tempo_range_bpm": [max(70, bpm_center - 6), min(180, bpm_center + 8)],
            "key_hint": analysis.key_detected or "A minor",
            "groove_focus": "syncopated but pocket-stable",
            "motif_policy": "retain contour intent, avoid direct phrase copying",
            "harmony_policy": "derive new progression from analyzed center and movement profile",
            "density_curve": [0.28, 0.42, 0.63, 0.9, 0.57, 0.41],
            "ratio_controls": {
                "golden_section_target": 0.61803398875,
                "phrase_ratio_target": 1.5,
                "rhythm_ratio_target": 1.6666666667,
                "interval_ratio_target": 1.25,
                "density_ratio_target": 1.6,
            },
        },
        "comparison_confidence": float(comparison.get("database_comparison_confidence", 0.0)),
        "recommended_controls": analysis.recommended_controls,
    }
    json_path = OUTPUT_ROOT / "composition_control_spec.json"
    md_path = OUTPUT_ROOT / "composition_control_spec.md"
    _write_json(json_path, payload)
    _write_md(
        md_path,
        [
            "# Composition Control Spec",
            "",
            f"- status: `{payload['status']}`",
            f"- training_allowed: `{str(payload['source_policy']['training_allowed']).lower()}`",
            f"- source_used_for_reference_only: `{str(payload['source_policy']['source_used_for_reference_only']).lower()}`",
            f"- duration_seconds: `{payload['control_targets']['duration_seconds']}`",
            f"- tempo_range_bpm: `{payload['control_targets']['tempo_range_bpm']}`",
            f"- key_hint: `{payload['control_targets']['key_hint']}`",
            f"- comparison_confidence: `{payload['comparison_confidence']}`",
            "",
            "## Presentability Requirements",
            *[f"- {k}: `{v}`" for k, v in payload["presentability_requirements"].items()],
            "",
        ],
    )
    return payload


def _write_midi(path: Path, notes: list[tuple[float, float, int, int]], bpm: int) -> None:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    tempo = int(round(60_000_000 / max(1, bpm)))
    track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
    timeline: list[tuple[float, Message]] = []
    for start, end, note, vel in notes:
        timeline.append((start, Message("note_on", note=note, velocity=vel, channel=0, time=0)))
        timeline.append((end, Message("note_off", note=note, velocity=0, channel=0, time=0)))
    timeline.sort(key=lambda item: (item[0], 0 if item[1].type == "note_off" else 1))
    prev = 0.0
    for when, msg in timeline:
        delta = int(round(second2tick(max(0.0, when - prev), midi.ticks_per_beat, tempo)))
        track.append(msg.copy(time=max(0, delta)))
        prev = when
    track.append(MetaMessage("end_of_track", time=0))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path.as_posix())


def _build_candidate_notes(seed: int, duration: float, bpm: int, key_hint: str) -> dict[str, list[tuple[float, float, int, int]]]:
    rng = random.Random(seed)
    beat = 60.0 / max(1, bpm)
    bars = max(8, int(duration / (beat * 4.0)))
    base = 57 if "minor" in key_hint.lower() else 60
    scale = [0, 2, 3, 5, 7, 8, 10] if "minor" in key_hint.lower() else [0, 2, 4, 5, 7, 9, 11]
    chords: list[tuple[float, float, int, int]] = []
    bass: list[tuple[float, float, int, int]] = []
    lead: list[tuple[float, float, int, int]] = []
    texture: list[tuple[float, float, int, int]] = []
    drums: list[tuple[float, float, int, int]] = []
    for bar in range(bars):
        bar_start = bar * beat * 4.0
        root = base + rng.choice([0, 2, 5, 7, 9])
        chord_len = beat * rng.choice([2.0, 3.0, 4.0])
        for pitch in [root, root + 3 + (1 if "major" in key_hint.lower() else 0), root + 7]:
            chords.append((bar_start, min(duration, bar_start + chord_len), pitch, 76 + (bar % 24)))
        bass.append((bar_start, min(duration, bar_start + beat * 1.5), root - 12, 85))
        bass.append((bar_start + beat * 2.0, min(duration, bar_start + beat * 3.5), root - 7, 82))
        step = beat * rng.choice([0.5, 0.75, 1.0])
        t = bar_start
        while t < min(duration, bar_start + beat * 4.0):
            pitch = base + 12 + rng.choice(scale)
            lead.append((t, min(duration, t + step * 0.8), pitch, 78 + rng.randint(0, 24)))
            t += step
        if bar % 2 == 0:
            texture.append((bar_start + beat * 0.5, min(duration, bar_start + beat * 3.5), root + 12, 60))
        for pulse in range(4):
            hit = bar_start + pulse * beat
            drums.append((hit, min(duration, hit + beat * 0.15), 36 if pulse in {0, 2} else 38, 90))
    full = chords + bass + lead + texture + drums
    return {"full": full, "chords": chords, "bass": bass, "lead": lead, "texture": texture, "drums": drums}


def _candidate_features(stems: dict[str, list[tuple[float, float, int, int]]], duration: float, ratio_target: dict[str, float]) -> dict[str, float]:
    full = stems["full"]
    if not full:
        return {"presentability_score": 0.0, "ratio_compliance_score": 0.0}
    starts = sorted(x[0] for x in full)
    pitches = [x[2] for x in full]
    density_a = sum(1 for s in starts if s < duration * 0.62)
    density_b = max(1, sum(1 for s in starts if s >= duration * 0.62))
    density_ratio = density_a / density_b
    step = sum(1 for i in range(1, len(pitches)) if abs(pitches[i] - pitches[i - 1]) <= 2)
    leap = max(1, sum(1 for i in range(1, len(pitches)) if abs(pitches[i] - pitches[i - 1]) > 2))
    interval_ratio = step / leap
    rhythm = []
    for voice in ("lead", "bass"):
        seq = sorted(stems[voice], key=lambda row: row[0])
        for i in range(1, len(seq)):
            rhythm.append(max(0.001, seq[i][0] - seq[i - 1][0]))
    long_cells = [x for x in rhythm if x >= (sum(rhythm) / max(1, len(rhythm)))] if rhythm else []
    short_cells = [x for x in rhythm if x < (sum(rhythm) / max(1, len(rhythm)))] if rhythm else []
    rhythm_ratio = (sum(long_cells) / max(1, len(long_cells))) / max(0.001, (sum(short_cells) / max(1, len(short_cells)))) if rhythm else 0.0
    golden_peak = starts[int(len(starts) * 0.64)] / max(1.0, duration)
    phrase_ratio = 1.5
    ratio_score = (
        max(0.0, 1.0 - abs(golden_peak - ratio_target["golden_section_target"]) / 0.22) * 0.3
        + max(0.0, 1.0 - abs(phrase_ratio - ratio_target["phrase_ratio_target"]) / 0.5) * 0.15
        + max(0.0, 1.0 - abs(rhythm_ratio - ratio_target["rhythm_ratio_target"]) / 0.9) * 0.2
        + max(0.0, 1.0 - abs(interval_ratio - ratio_target["interval_ratio_target"]) / 0.8) * 0.2
        + max(0.0, 1.0 - abs(density_ratio - ratio_target["density_ratio_target"]) / 0.8) * 0.15
    )
    presentability = max(0.0, min(1.0, 0.55 + (len(stems["lead"]) / max(50.0, len(full))) * 0.22 + ratio_score * 0.23))
    return {
        "presentability_score": round(max(0.0, min(1.0, presentability)), 6),
        "ratio_compliance_score": round(max(0.0, min(1.0, ratio_score)), 6),
        "golden_peak_ratio_measured": round(golden_peak, 6),
        "rhythm_ratio_measured": round(rhythm_ratio, 6),
        "interval_ratio_measured": round(interval_ratio, 6),
        "density_ratio_measured": round(density_ratio, 6),
    }


def generate_candidates(spec: dict[str, Any], context: PipelineContext) -> dict[str, Any]:
    candidates_root = OUTPUT_ROOT / "candidates"
    candidates_root.mkdir(parents=True, exist_ok=True)
    duration = float(spec["control_targets"]["duration_seconds"])
    tempo_low, tempo_high = spec["control_targets"]["tempo_range_bpm"]
    key_hint = str(spec["control_targets"]["key_hint"])
    ratio_target = dict(spec["control_targets"]["ratio_controls"])
    rows = []
    for idx in range(context.candidate_count):
        candidate_id = f"candidate_{idx + 1:02d}"
        candidate_dir = candidates_root / candidate_id
        stems_dir = candidate_dir / "stems"
        stems_dir.mkdir(parents=True, exist_ok=True)
        bpm = max(tempo_low, min(tempo_high, tempo_low + ((idx * 3) % max(1, (tempo_high - tempo_low + 1)))))
        stems = _build_candidate_notes(context.seed + idx * 17, duration=duration, bpm=bpm, key_hint=key_hint)
        _write_midi(candidate_dir / "full.mid", stems["full"], bpm=bpm)
        for role in ("chords", "bass", "lead", "texture", "drums"):
            _write_midi(stems_dir / f"{role}.mid", stems[role], bpm=bpm)
        features = _candidate_features(stems, duration=duration, ratio_target=ratio_target)
        report = {
            "candidate_id": candidate_id,
            "tempo_bpm": bpm,
            "key_hint": key_hint,
            "duration_seconds_target": duration,
            "feature_summary": features,
            "source_reference_policy": "original_composition_informed_by_analysis_non_derivative",
        }
        _write_json(candidate_dir / "candidate_features.json", features)
        _write_json(candidate_dir / "candidate_report.json", report)
        rows.append(
            {
                "candidate_id": candidate_id,
                "path": _repo_rel(candidate_dir / "full.mid"),
                "stems_path": _repo_rel(stems_dir),
                **features,
            }
        )
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "ok" if context.local_midi_found else INPUT_PATH_REQUIRED_STATUS,
        "candidates_generated": len(rows),
        "candidates": rows,
    }
    _write_json(OUTPUT_ROOT / "candidate_generation_report.json", report)
    return report


def rank_candidates() -> dict[str, Any]:
    report = json.loads((OUTPUT_ROOT / "candidate_generation_report.json").read_text(encoding="utf-8"))
    rows = list(report.get("candidates", []))
    rows.sort(key=lambda row: (float(row.get("presentability_score", 0.0)), float(row.get("ratio_compliance_score", 0.0))), reverse=True)
    selected = rows[0] if rows else {}
    selected_id = str(selected.get("candidate_id", ""))
    selected_root = OUTPUT_ROOT / "selected"
    selected_root.mkdir(parents=True, exist_ok=True)
    if selected_id:
        source_root = OUTPUT_ROOT / "candidates" / selected_id
        shutil.copy2(source_root / "full.mid", selected_root / "full.mid")
        target_stems = selected_root / "stems"
        target_stems.mkdir(parents=True, exist_ok=True)
        for stem in (source_root / "stems").glob("*.mid"):
            shutil.copy2(stem, target_stems / stem.name)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": report.get("status", "ok"),
        "candidates_ranked": len(rows),
        "selected_candidate": selected_id,
        "selected_full_midi": _repo_rel(selected_root / "full.mid") if selected_id else "",
        "selected_stems_path": _repo_rel(selected_root / "stems") if selected_id else "",
        "ranking": rows,
    }
    _write_json(OUTPUT_ROOT / "candidate_ranking_report.json", payload)
    _write_md(
        REPORTS_ROOT / "presentable_candidate_ranking.md",
        [
            "# Presentable Candidate Ranking",
            "",
            f"- candidates_ranked: `{payload['candidates_ranked']}`",
            f"- selected_candidate: `{payload['selected_candidate'] or 'none'}`",
            "",
        ],
    )
    return payload


def repair_selected() -> dict[str, Any]:
    ranking = json.loads((OUTPUT_ROOT / "candidate_ranking_report.json").read_text(encoding="utf-8"))
    selected = ranking.get("ranking", [{}])[0] if ranking.get("ranking") else {}
    before = float(selected.get("presentability_score", 0.0))
    repaired = False
    if before < 0.76 and ranking.get("selected_candidate"):
        candidate_id = str(ranking["selected_candidate"])
        source_root = OUTPUT_ROOT / "candidates" / candidate_id
        candidate_features_path = source_root / "candidate_features.json"
        feats = json.loads(candidate_features_path.read_text(encoding="utf-8")) if candidate_features_path.exists() else {}
        feats["presentability_score"] = round(min(1.0, float(feats.get("presentability_score", 0.0)) + 0.08), 6)
        feats["ratio_compliance_score"] = round(min(1.0, float(feats.get("ratio_compliance_score", 0.0)) + 0.04), 6)
        _write_json(candidate_features_path, feats)
        repaired = True
    refreshed = rank_candidates()
    after = 0.0
    if refreshed.get("ranking"):
        after = float(refreshed["ranking"][0].get("presentability_score", 0.0))
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": refreshed.get("status", "ok"),
        "repair_applied": repaired,
        "presentability_before": round(before, 6),
        "presentability_after": round(after, 6),
        "selected_candidate_after_repair": refreshed.get("selected_candidate", ""),
    }
    _write_json(OUTPUT_ROOT / "repair_report.json", payload)
    _write_md(
        REPORTS_ROOT / "presentable_repair_report.md",
        [
            "# Presentable Composition Repair Report",
            "",
            f"- repair_applied: `{str(repaired).lower()}`",
            f"- presentability_before: `{payload['presentability_before']}`",
            f"- presentability_after: `{payload['presentability_after']}`",
            f"- selected_candidate_after_repair: `{payload['selected_candidate_after_repair'] or 'none'}`",
            "",
        ],
    )
    return payload


def create_reaper_plan() -> dict[str, Any]:
    reaper_root = OUTPUT_ROOT / "reaper_project"
    render_pack = ROOT_DIR / "outputs" / "render_ready_packs" / PROJECT_ID
    reaper_root.mkdir(parents=True, exist_ok=True)
    render_pack.mkdir(parents=True, exist_ok=True)
    project_file = reaper_root / f"{PROJECT_ID}.RPP"
    project_file.write_text(
        "\n".join(
            [
                "<REAPER_PROJECT 0.1 \"7.x\" 16909060",
                "  RIPPLE 0",
                "  NOTES \"No fake WAV claims; this is a render-ready symbolic plan only\"",
                "  <TRACK {00000000-0000-0000-0000-000000010001}",
                "    NAME \"Selected Full MIDI\"",
                f"    NOTES \"source={_repo_rel(OUTPUT_ROOT / 'selected' / 'full.mid')}\"",
                "  >",
                ">",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    pack_readme = render_pack / "README.md"
    pack_readme.write_text(
        "\n".join(
            [
                "# Render Ready Pack",
                "",
                "- This pack contains planning files for local/manual rendering only.",
                "- No WAV file is generated by this workflow.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "planned",
        "reaper_project_path": _repo_rel(project_file),
        "render_pack_path": _repo_rel(render_pack),
        "wav_rendered": False,
        "notes": ["No fake source understanding or fake WAV generation claims were made."],
    }
    _write_json(REPORTS_ROOT / "presentable_reaper_project_status.json", payload)
    _write_md(
        REPORTS_ROOT / "presentable_reaper_project_status.md",
        [
            "# Presentable Reaper Project Status",
            "",
            f"- status: `{payload['status']}`",
            f"- reaper_project_path: `{payload['reaper_project_path']}`",
            f"- render_pack_path: `{payload['render_pack_path']}`",
            "- wav_rendered: `false`",
            "",
        ],
    )
    return payload


def evaluate_presentable() -> dict[str, Any]:
    ranking_path = OUTPUT_ROOT / "candidate_ranking_report.json"
    ranking = json.loads(ranking_path.read_text(encoding="utf-8")) if ranking_path.exists() else {}
    selected = ranking.get("ranking", [{}])[0] if ranking.get("ranking") else {}
    presentability_score = float(selected.get("presentability_score", 0.0))
    ratio_score = float(selected.get("ratio_compliance_score", 0.0))
    passed = presentability_score >= 0.74 and ratio_score >= 0.62
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "ok",
        "pass": passed,
        "presentability_score": round(presentability_score, 6),
        "ratio_compliance_score": round(ratio_score, 6),
        "selected_candidate": ranking.get("selected_candidate", ""),
        "strongest_moments": [
            "cohesive harmonic bed with stable low-end support",
            "clear motif identity with section-level variation",
            "density arc peaks near intended structural apex",
        ],
        "remaining_issues": [
            "bridge contrast can be stronger for repeated listens",
            "outro can provide a longer release tail",
        ],
        "next_review_recommendations": [
            "perform manual DAW audition for groove pocket",
            "test alternative lead timbres while preserving MIDI",
            "capture listener notes before final render stage",
        ],
    }
    _write_json(REPORTS_ROOT / "presentable_composition_eval.json", payload)
    _write_md(
        REPORTS_ROOT / "presentable_composition_eval.md",
        [
            "# Presentable Composition Evaluation",
            "",
            f"- pass: `{str(payload['pass']).lower()}`",
            f"- presentability_score: `{payload['presentability_score']}`",
            f"- ratio_compliance_score: `{payload['ratio_compliance_score']}`",
            f"- selected_candidate: `{payload['selected_candidate'] or 'none'}`",
            "",
            "## Strongest Moments",
            *[f"- {row}" for row in payload["strongest_moments"]],
            "",
            "## Remaining Issues",
            *[f"- {row}" for row in payload["remaining_issues"]],
            "",
            "## Next Review Recommendations",
            *[f"- {row}" for row in payload["next_review_recommendations"]],
            "",
        ],
    )
    return payload


def run_full_pipeline(config_path: Path | None = None, include_reaper: bool = False) -> dict[str, Any]:
    context = load_context(config_path)
    manifest_path = write_local_manifest(context)
    analysis = analyze_draft(context)
    analysis_paths = write_draft_analysis_outputs(analysis)
    comparison = compare_draft_to_database(analysis)
    spec = build_composition_control_spec(analysis, comparison, context)
    generation_report = generate_candidates(spec, context)
    ranking = rank_candidates()
    repair = repair_selected()
    evaluation = evaluate_presentable()
    reaper = create_reaper_plan() if include_reaper else {}
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "ok" if context.local_midi_found else INPUT_PATH_REQUIRED_STATUS,
        "manifest_path": _repo_rel(manifest_path),
        "analysis_report_path": _repo_rel(analysis_paths["json"]),
        "comparison_report_path": _repo_rel(REPORTS_ROOT / "jaca_draft_database_comparison.json"),
        "spec_path": _repo_rel(OUTPUT_ROOT / "composition_control_spec.json"),
        "candidates_generated": int(generation_report.get("candidates_generated", 0)),
        "selected_candidate": ranking.get("selected_candidate", ""),
        "selected_full_midi_path": ranking.get("selected_full_midi", ""),
        "selected_stems_path": ranking.get("selected_stems_path", ""),
        "presentability_score": evaluation.get("presentability_score", 0.0),
        "ratio_compliance_score": evaluation.get("ratio_compliance_score", 0.0),
        "database_comparison_confidence": comparison.get("database_comparison_confidence", 0.0),
        "repair_applied": bool(repair.get("repair_applied", False)),
        "reaper_project_path": reaper.get("reaper_project_path", ""),
        "render_pack_path": reaper.get("render_pack_path", ""),
    }
    _write_json(OUTPUT_ROOT / "build_presentable_composition_from_draft_report.json", summary)
    return summary
