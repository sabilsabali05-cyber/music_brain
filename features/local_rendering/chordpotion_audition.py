from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .chordpotion_intent_schema import ChordPotionTargetIntent, write_target_intent
from .chordpotion_output_analysis import analyze_transformed_midi
from .chordpotion_preset_registry import ChordPotionPresetProfile
from .chordpotion_scoring import ChordPotionCandidateScore, score_candidate_against_intent, select_best_candidate


@dataclass
class AuditionCandidateResult:
    preset_id: str
    display_name: str
    transformed_midi_captured: bool
    transformed_midi_path: str
    wav_preview_rendered: bool
    wav_preview_path: str
    analysis: dict
    machine_scores: dict
    overall_candidate_score: float
    blocked_reason: str

    def as_dict(self) -> dict:
        return {
            "preset_id": self.preset_id,
            "display_name": self.display_name,
            "transformed_midi_captured": self.transformed_midi_captured,
            "transformed_midi_path": self.transformed_midi_path,
            "wav_preview_rendered": self.wav_preview_rendered,
            "wav_preview_path": self.wav_preview_path,
            "analysis": self.analysis,
            "machine_scores": self.machine_scores,
            "overall_candidate_score": self.overall_candidate_score,
            "blocked_reason": self.blocked_reason,
        }


@dataclass
class AuditionResult:
    audition_id: str
    output_dir: Path
    candidate_results: list[AuditionCandidateResult]
    selected_preset: str
    blocked_by_local_config: bool
    blocker: str


def _repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _candidate_paths(repo_root: Path, audition_id: str, preset: ChordPotionPresetProfile) -> tuple[Path, Path]:
    safe_preset = preset.preset_id.replace(" ", "_")
    transformed = repo_root / "outputs" / "chordpotion_auditions" / audition_id / "candidates" / safe_preset / "transformed.mid"
    preview = repo_root / "renders" / "chordpotion_auditions" / audition_id / "candidates" / safe_preset / "preview.wav"
    return transformed, preview


def run_chordpotion_audition(
    repo_root: Path,
    harmony_skeleton_path: Path,
    target_intent: ChordPotionTargetIntent,
    presets: list[ChordPotionPresetProfile],
    theory_profile: str = "",
    texture_profile: str = "",
    audition_id: str | None = None,
) -> AuditionResult:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    audition_id = audition_id or f"{target_intent.intent_id}_{timestamp}"
    output_dir = repo_root / "outputs" / "chordpotion_auditions" / audition_id
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(harmony_skeleton_path, output_dir / "input_harmony_skeleton.mid")
    write_target_intent(output_dir / "target_intent.json", target_intent)

    candidate_results: list[AuditionCandidateResult] = []
    scored: dict[str, ChordPotionCandidateScore] = {}
    observed_any = False
    for preset in presets:
        transformed_path, preview_path = _candidate_paths(repo_root, audition_id, preset)
        transformed_captured = transformed_path.exists()
        wav_preview_rendered = preview_path.exists() and preview_path.is_file() and preview_path.stat().st_size > 0
        observed_any = observed_any or transformed_captured or wav_preview_rendered
        analysis = analyze_transformed_midi(transformed_path if transformed_captured else Path("missing.mid"))
        score = score_candidate_against_intent(
            intent=target_intent,
            preset=preset,
            analysis=analysis,
            theory_profile=theory_profile,
            texture_profile=texture_profile,
        )
        scored[preset.preset_id] = score
        blocked_reason = ""
        if not transformed_captured and not wav_preview_rendered:
            blocked_reason = "blocked_by_local_config"
        candidate_results.append(
            AuditionCandidateResult(
                preset_id=preset.preset_id,
                display_name=preset.display_name,
                transformed_midi_captured=transformed_captured,
                transformed_midi_path=_repo_relative(transformed_path, repo_root) if transformed_captured else "",
                wav_preview_rendered=wav_preview_rendered,
                wav_preview_path=_repo_relative(preview_path, repo_root) if wav_preview_rendered else "",
                analysis=analysis.as_dict(),
                machine_scores=score.as_dict(),
                overall_candidate_score=score.overall_candidate_score,
                blocked_reason=blocked_reason,
            )
        )

    selected_preset = select_best_candidate(scored)
    blocked = not observed_any
    blocker = "blocked_by_local_config" if blocked else ""
    (output_dir / "candidate_results.json").write_text(
        json.dumps([item.as_dict() for item in candidate_results], indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "selected_preset.json").write_text(
        json.dumps(
            {
                "selected_preset": selected_preset,
                "selection_rule": "max_overall_candidate_score",
                "blocked_by_local_config": blocked,
                "blocker": blocker,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "audition_report.md").write_text(
        "\n".join(
            [
                "# ChordPotion Preset Audition Report",
                "",
                f"- audition_id: `{audition_id}`",
                f"- presets_considered: `{len(presets)}`",
                f"- selected_preset: `{selected_preset or 'none'}`",
                f"- blocked_by_local_config: `{str(blocked).lower()}`",
                f"- blocker: `{blocker or 'none'}`",
                "",
                "## Candidate Summary",
            ]
            + [
                (
                    f"- `{item.preset_id}` score={item.overall_candidate_score:.3f} "
                    f"midi={str(item.transformed_midi_captured).lower()} "
                    f"wav_preview={str(item.wav_preview_rendered).lower()}"
                )
                for item in candidate_results
            ]
            + [""],
        ),
        encoding="utf-8",
    )
    return AuditionResult(
        audition_id=audition_id,
        output_dir=output_dir,
        candidate_results=candidate_results,
        selected_preset=selected_preset,
        blocked_by_local_config=blocked,
        blocker=blocker,
    )
