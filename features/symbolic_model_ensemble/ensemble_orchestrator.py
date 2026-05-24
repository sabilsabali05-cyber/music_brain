from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mido import Message, MidiFile, MidiTrack, second2tick

from features.symbolic_ir import (
    SymbolicEvaluationScore,
    SymbolicGenerationCandidate,
    SymbolicGenerationRequest,
    SymbolicPromptSpec,
)
from features.symbolic_model_ensemble.capability_registry import build_backend_registry

ROOT_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT_DIR / "outputs" / "symbolic_ensemble_v1"
ROUTING_REPORT_DIR = ROOT_DIR / "reports" / "symbolic_backends"


def _to_repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        parts = path.resolve().as_posix().split("/")
        tail = "/".join(parts[-4:]) if len(parts) >= 4 else path.name
        return f"<LOCAL_PATH>/{tail}"


class SymbolicEnsembleOrchestrator:
    def __init__(self) -> None:
        self.registry = build_backend_registry()

    def _build_request(self, prompt: str, backend_id: str, task_type: str) -> SymbolicGenerationRequest:
        return SymbolicGenerationRequest(
            request_id=uuid.uuid4().hex[:12],
            prompt_spec=SymbolicPromptSpec(
                prompt_text=prompt,
                duration_seconds=96.0,
                tempo=120.0,
                meter="4/4",
                key_hint="unknown",
                ratio_plan="golden_ratio_climax",
                section_labels=["intro", "build", "climax", "release"],
                requested_track_roles=["drums", "bass", "chords", "lead"],
                prompt_constraints={"human_review_required": True},
            ),
            task_type=task_type,
            source_backend=backend_id,
            conditioning={},
        )

    @staticmethod
    def symbolic_routing_plan() -> dict[str, Any]:
        return {
            "status": "ok",
            "moonbeam_preferred_for": [
                "continuation",
                "infill",
                "section development",
                "phrase development",
                "symbolic composition",
            ],
            "midigpt_preferred_for": [
                "drums",
                "groove",
                "density variation",
                "multitrack infill",
                "bar-level infill",
                "track-level infill",
                "drum variation",
            ],
            "text2midi_preferred_for": [
                "prompt sketch",
            ],
            "musicbert_preferred_for": [
                "ranking",
                "evaluation",
                "symbolic similarity",
                "accompaniment fit",
                "melody fit",
                "taste-ranker future target",
            ],
            "fallback_policy": "example_retrieval_only_when_no_real_symbolic_backend_available",
            "model_training_has_occurred": False,
            "limitations": [
                "Routing priority does not force availability.",
                "Unavailable backends are reported explicitly and do not silently generate.",
            ],
        }

    def write_routing_report(self, report_dir: Path = ROUTING_REPORT_DIR) -> tuple[Path, Path, dict[str, Any]]:
        payload = self.symbolic_routing_plan()
        report_dir.mkdir(parents=True, exist_ok=True)
        json_path = report_dir / "symbolic_routing_plan.json"
        md_path = report_dir / "symbolic_routing_plan.md"
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        lines = [
            "# Symbolic Routing Plan",
            "",
            "## Preferred Routing",
            "- Moonbeam: continuation, infill, section development, phrase development, symbolic composition",
            "- MIDI-GPT: drums, groove, density variation, multitrack infill, bar-level infill, track-level infill, drum variation",
            "- Text2MIDI: prompt sketch",
            "- MusicBERT: ranking, evaluation, symbolic similarity, accompaniment fit, melody fit, taste-ranker future target",
            "",
            "## Fallback",
            "- example_retrieval_only_when_no_real_symbolic_backend_available",
            "",
            "- model_training_has_occurred: `False`",
        ]
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return json_path, md_path, payload

    def _write_backend_availability(self, output_root: Path) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        for backend_id, adapter in self.registry.items():
            cap = adapter.check_available()
            rows.append(asdict(cap))
        payload = {
            "status": "ok",
            "backends": rows,
            "limitations": [
                "Real backends remain optional until local config/dependencies/weights are provided.",
                "Availability does not imply generation quality or model training on user data.",
            ],
        }
        json_path = output_root / "backend_availability_report.json"
        md_path = output_root / "backend_availability_report.md"
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        lines = ["# Backend Availability Report", ""]
        for row in rows:
            lines.append(f"- `{row['backend_id']}`: `{row['status']}` reason=`{row['reason']}`")
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return payload

    def _score_candidates(self, candidates: list[SymbolicGenerationCandidate]) -> list[SymbolicEvaluationScore]:
        scored: list[SymbolicEvaluationScore] = []
        for candidate in candidates:
            note_count = sum(len(track.note_events) for track in candidate.ir.tracks)
            score = min(1.0, note_count / 16.0)
            scored.append(
                SymbolicEvaluationScore(
                    candidate_id=candidate.candidate_id,
                    evaluated_by="heuristic_fallback",
                    score=score,
                    metrics={"note_count": float(note_count)},
                    rationale="MusicBERT unavailable; used deterministic note-count heuristic.",
                )
            )
        scored.sort(key=lambda row: row.score, reverse=True)
        return scored

    def _write_candidate_midi(self, candidate: SymbolicGenerationCandidate, midi_path: Path) -> int:
        midi = MidiFile(ticks_per_beat=480)
        tempo = int(round(60_000_000.0 / max(1.0, candidate.ir.tempo)))
        note_count = 0
        for idx, track_ir in enumerate(candidate.ir.tracks):
            midi_track = MidiTrack()
            midi.tracks.append(midi_track)
            timeline: list[tuple[float, Message]] = []
            for note in track_ir.note_events:
                start_sec = max(0.0, note.start_tick / 480.0 * (60.0 / max(1.0, candidate.ir.tempo)))
                end_sec = max(start_sec + 0.05, (note.start_tick + note.duration_tick) / 480.0 * (60.0 / max(1.0, candidate.ir.tempo)))
                timeline.append((start_sec, Message("note_on", note=max(0, min(127, note.pitch)), velocity=max(1, min(127, note.velocity)), channel=note.channel, time=0)))
                timeline.append((end_sec, Message("note_off", note=max(0, min(127, note.pitch)), velocity=0, channel=note.channel, time=0)))
            timeline.sort(key=lambda item: (item[0], 0 if item[1].type == "note_off" else 1))
            prev = 0.0
            for at_sec, message in timeline:
                delta = max(0.0, at_sec - prev)
                ticks = int(round(second2tick(delta, midi.ticks_per_beat, tempo)))
                if idx == 0 and prev == 0.0:
                    midi_track.append(Message("program_change", program=0, channel=message.channel, time=0))
                midi_track.append(message.copy(time=max(0, ticks)))
                prev = at_sec
                if message.type == "note_on" and message.velocity > 0:
                    note_count += 1
        midi_path.parent.mkdir(parents=True, exist_ok=True)
        midi.save(midi_path.as_posix())
        return note_count

    def generate(self, prompt: str, *, output_root: Path = OUT_DIR) -> dict[str, Any]:
        output_root.mkdir(parents=True, exist_ok=True)
        candidates_dir = output_root / "generated_candidates"
        candidates_dir.mkdir(parents=True, exist_ok=True)

        availability = self._write_backend_availability(output_root)
        by_id = {row["backend_id"]: row for row in availability["backends"]}
        real_backends = ["text2midi", "moonbeam", "midigpt", "musicbert"]
        no_real_symbolic_backend_available = all(by_id.get(name, {}).get("status") != "available" for name in real_backends)

        candidates: list[SymbolicGenerationCandidate] = []
        used_steps: list[dict[str, str]] = []

        text2midi_req = self._build_request(prompt, "text2midi", "prompt_sketch")
        text2midi_res = self.registry["text2midi"].generate(text2midi_req)
        used_steps.append({"backend": "text2midi", "status": text2midi_res.status, "reason": text2midi_res.reason})
        if text2midi_res.candidate is not None:
            candidates.append(text2midi_res.candidate)

        moonbeam_req = self._build_request(prompt, "moonbeam", "symbolic_composition")
        moonbeam_res = self.registry["moonbeam"].continue_ir(moonbeam_req)
        used_steps.append({"backend": "moonbeam", "status": moonbeam_res.status, "reason": moonbeam_res.reason})
        if moonbeam_res.candidate is not None:
            candidates.append(moonbeam_res.candidate)

        midigpt_req = self._build_request(prompt, "midigpt", "drum_multitrack_variation")
        midigpt_req.conditioning["preferred_roles"] = ["drums", "bass", "chords"]
        midigpt_res = self.registry["midigpt"].infill_ir(midigpt_req)
        used_steps.append({"backend": "midigpt", "status": midigpt_res.status, "reason": midigpt_res.reason})
        if midigpt_res.candidate is not None:
            candidates.append(midigpt_res.candidate)

        fallback_used = False
        if not candidates:
            fallback_req = self._build_request(prompt, "example_retrieval", "fallback_example_retrieval")
            fallback_res = self.registry["example_retrieval"].generate(fallback_req)
            used_steps.append({"backend": "example_retrieval", "status": fallback_res.status, "reason": fallback_res.reason})
            if fallback_res.candidate is not None:
                fallback_res.candidate.ir.provenance_flags["example_retrieval_fallback"] = True
                candidates.append(fallback_res.candidate)
                fallback_used = True

        if not candidates:
            raise RuntimeError("No symbolic candidate could be produced (including fallback).")

        evaluation_scores = self._score_candidates(candidates)
        score_map = {item.candidate_id: item.score for item in evaluation_scores}
        selected = sorted(candidates, key=lambda item: score_map.get(item.candidate_id, 0.0), reverse=True)[0]

        candidate_rows: list[dict[str, Any]] = []
        for candidate in candidates:
            candidate_ir_path = candidates_dir / f"{candidate.candidate_id}.ir.json"
            candidate_midi_path = candidates_dir / f"{candidate.candidate_id}.mid"
            note_count = self._write_candidate_midi(candidate, candidate_midi_path)
            candidate_ir_path.write_text(json.dumps(asdict(candidate), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
            candidate_rows.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "backend": candidate.source_backend,
                    "score": score_map.get(candidate.candidate_id, 0.0),
                    "note_count": note_count,
                    "candidate_ir_json": _to_repo_relative(candidate_ir_path),
                    "candidate_midi": _to_repo_relative(candidate_midi_path),
                }
            )

        selected_ir_json = output_root / "selected_candidate_ir.json"
        selected_midi = output_root / "selected_candidate.mid"
        selected_ir_json.write_text(json.dumps(asdict(selected), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        selected_note_count = self._write_candidate_midi(selected, selected_midi)

        report = {
            "status": "ok",
            "prompt_text": prompt,
            "used_steps": used_steps,
            "candidates": candidate_rows,
            "selected_candidate_id": selected.candidate_id,
            "selected_candidate_backend": selected.source_backend,
            "selected_candidate_note_count": selected_note_count,
            "selected_candidate_midi": _to_repo_relative(selected_midi),
            "selected_candidate_ir_json": _to_repo_relative(selected_ir_json),
            "backend_availability_report_json": _to_repo_relative(output_root / "backend_availability_report.json"),
            "backend_availability_report_md": _to_repo_relative(output_root / "backend_availability_report.md"),
            "example_retrieval_fallback": fallback_used,
            "no_real_symbolic_backend_available": no_real_symbolic_backend_available,
            "not_model_trained_on_user_data": True,
            "limitations": [
                "No model weights are downloaded by this workflow.",
                "No training is performed.",
                "When real backends are unavailable, fallback uses existing example retrieval prototype.",
            ],
        }
        report_json = output_root / "ensemble_generation_report.json"
        report_md = output_root / "ensemble_generation_report.md"
        report_json.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        lines = [
            "# Symbolic Ensemble Generation Report",
            "",
            f"- prompt_text: `{prompt}`",
            f"- selected_candidate_backend: `{report['selected_candidate_backend']}`",
            f"- example_retrieval_fallback: `{report['example_retrieval_fallback']}`",
            f"- no_real_symbolic_backend_available: `{report['no_real_symbolic_backend_available']}`",
            f"- not_model_trained_on_user_data: `{report['not_model_trained_on_user_data']}`",
            "",
            "## Backend Steps",
        ]
        for step in used_steps:
            lines.append(f"- `{step['backend']}` status=`{step['status']}` reason=`{step['reason']}`")
        lines.extend(["", "## Selected Output"])
        lines.append(f"- MIDI: `{report['selected_candidate_midi']}`")
        lines.append(f"- IR: `{report['selected_candidate_ir_json']}`")
        report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return report
