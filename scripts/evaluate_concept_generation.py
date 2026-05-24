from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from mido import MidiFile

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.concept_to_composition.concept_review_schema import (  # noqa: E402
    CandidateEvaluation,
    ConceptGenerationEvaluation,
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _midi_parses(path: Path) -> bool:
    try:
        MidiFile(path.as_posix())
    except Exception:
        return False
    return True


def _score_candidate(candidate_dir: Path) -> CandidateEvaluation:
    alignment = _load_json(candidate_dir / "concept_alignment_report.json")
    generation = _load_json(candidate_dir / "generation_report.json")
    midi_ok = _midi_parses(candidate_dir / "full.mid")
    avoid_patterns = generation.get("avoid_patterns_applied", [])
    preserve_patterns = generation.get("preserve_patterns_applied", [])

    return CandidateEvaluation(
        candidate_name=candidate_dir.name,
        concept_alignment_score=float(alignment.get("concept_alignment_score", 0.0)),
        emotional_arc_score=float(alignment.get("emotional_arc_score", 0.0)),
        harmony_score=float(alignment.get("harmony_score", 0.0)),
        voice_leading_score=float(alignment.get("voice_leading_score", 0.0)),
        rhythm_identity_score=float(alignment.get("rhythm_identity_score", 0.0)),
        texture_intent_score=float(alignment.get("texture_intent_score", 0.0)),
        random_note_penalty=0.0 if any("random interval jumps" in item for item in avoid_patterns) else 0.2,
        clutter_penalty=0.02 if any("clutter" in item for item in avoid_patterns) else 0.15,
        weirdness_musicality_score=float(alignment.get("weirdness_musicality_score", 0.0)),
        midi_parse_success=midi_ok and bool(preserve_patterns),
    )


def main() -> int:
    outputs_root = ROOT_DIR / "outputs" / "concept_song_idea_001"
    report_dir = ROOT_DIR / "reports" / "concept_to_composition"
    report_dir.mkdir(parents=True, exist_ok=True)

    candidates = sorted(path for path in outputs_root.iterdir() if path.is_dir() and path.name.startswith("candidate_"))
    evaluations = [_score_candidate(candidate) for candidate in candidates]
    ranked = sorted(evaluations, key=lambda item: item.concept_alignment_score, reverse=True)
    best = ranked[0] if ranked else CandidateEvaluation(
        candidate_name="none",
        concept_alignment_score=0.0,
        emotional_arc_score=0.0,
        harmony_score=0.0,
        voice_leading_score=0.0,
        rhythm_identity_score=0.0,
        texture_intent_score=0.0,
        random_note_penalty=1.0,
        clutter_penalty=1.0,
        weirdness_musicality_score=0.0,
        midi_parse_success=False,
    )
    summary = (
        f"Best candidate by concept alignment is {best.candidate_name} "
        f"with score {best.concept_alignment_score:.3f}; all outputs are local rule-based."
    )
    payload = ConceptGenerationEvaluation(
        concept_id="song_idea_001",
        best_candidate=best.candidate_name,
        candidates=evaluations,
        summary=summary,
    )

    json_path = report_dir / "song_idea_001_eval.json"
    md_path = report_dir / "song_idea_001_eval.md"
    json_path.write_text(payload.model_dump_json(indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Concept Generation Evaluation",
        "",
        f"- concept_id: {payload.concept_id}",
        f"- best_candidate: {payload.best_candidate}",
        f"- summary: {payload.summary}",
        "",
        "## Candidate Scores",
    ]
    for candidate in payload.candidates:
        lines.append(
            f"- {candidate.candidate_name}: alignment={candidate.concept_alignment_score:.3f}, "
            f"emotional_arc={candidate.emotional_arc_score:.3f}, harmony={candidate.harmony_score:.3f}, "
            f"voice_leading={candidate.voice_leading_score:.3f}, rhythm_identity={candidate.rhythm_identity_score:.3f}, "
            f"texture_intent={candidate.texture_intent_score:.3f}, random_note_penalty={candidate.random_note_penalty:.3f}, "
            f"clutter_penalty={candidate.clutter_penalty:.3f}, weirdness_musicality={candidate.weirdness_musicality_score:.3f}, "
            f"MIDI_parse_success={candidate.midi_parse_success}"
        )
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"CONCEPT_EVAL_JSON={json_path.as_posix()}")
    print(f"CONCEPT_EVAL_MD={md_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
