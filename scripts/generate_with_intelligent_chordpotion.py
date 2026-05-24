from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.local_rendering.chordpotion_audition import run_chordpotion_audition  # noqa: E402
from features.local_rendering.chordpotion_intent_schema import (  # noqa: E402
    ChordPotionTargetIntent,
    ChordPotionTargetPatternFamily,
    write_target_intent,
)
from features.local_rendering.chordpotion_preset_registry import load_preset_profiles_from_vst_registry  # noqa: E402
from features.local_rendering.chordpotion_selector import select_candidate_presets  # noqa: E402


def _run(script_name: str) -> None:
    result = subprocess.run([sys.executable, str(ROOT_DIR / "scripts" / script_name)], capture_output=True, text=True, cwd=ROOT_DIR, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{script_name} failed\n{result.stdout}\n{result.stderr}")


def main() -> int:
    generation_id = "intelligent_chordpotion_generation_v1"
    output_root = ROOT_DIR / "outputs" / generation_id
    output_root.mkdir(parents=True, exist_ok=True)

    _run("generate_chordpotion_ready_skeleton.py")
    _run("build_chordpotion_transform_plan.py")

    source_root = ROOT_DIR / "outputs" / "chordpotion_generation_v1"
    for name in ("harmony_skeleton.mid", "bass.mid", "lead_guide.mid"):
        src = source_root / name
        if src.exists():
            (output_root / name).write_bytes(src.read_bytes())

    target_intent = ChordPotionTargetIntent(
        intent_id="intelligent_intent_v1",
        source_generation_id=generation_id,
        target_role="chord_pattern_generator",
        source_chord_skeleton=(Path("outputs") / generation_id / "harmony_skeleton.mid").as_posix(),
        target_pattern_family=ChordPotionTargetPatternFamily.ROLLING_CHORD_MOTION,
        target_density=0.45,
        target_syncopation=0.4,
        target_motion=0.55,
        target_repetition=0.5,
        target_variation=0.5,
        target_humanization=0.4,
        target_register_behavior="mid_register_support",
        preserve_bass=True,
        preserve_top_voice=True,
        preserve_harmonic_rhythm=True,
        preserve_chord_identity=True,
        avoid_mud=True,
        avoid_random_keyboard_effect=True,
        avoid_overbusy_output=True,
        avoid_lead_conflict=True,
        desired_ear_effect="musical movement without clutter",
        texture_profile="warm_emotional_chord_bed",
        theory_profile="functional_harmony",
        confidence=0.72,
    )
    write_target_intent(output_root / "target_intent.json", target_intent)

    profiles = load_preset_profiles_from_vst_registry(ROOT_DIR / "config" / "local_vst_registry.local.json", "chordpotion_midi_fx")
    if not profiles:
        profiles = load_preset_profiles_from_vst_registry(ROOT_DIR / "config" / "local_vst_registry.example.json", "chordpotion_midi_fx")

    selector = select_candidate_presets(
        intent=target_intent,
        theory_profile=target_intent.theory_profile,
        texture_profile=target_intent.texture_profile,
        preset_profiles=profiles,
        previous_audition_outcomes_path=ROOT_DIR / "datasets" / "chordpotion" / "chordpotion_audition_outcomes.jsonl",
        human_feedback_path=ROOT_DIR / "datasets" / "chordpotion" / "chordpotion_feedback.example.jsonl",
        trained_ranker_path=ROOT_DIR / "artifacts" / "model_training" / "chordpotion_preset_selector" / "model.json",
        top_k=4,
    )
    audition = run_chordpotion_audition(
        repo_root=ROOT_DIR,
        harmony_skeleton_path=output_root / "harmony_skeleton.mid",
        target_intent=target_intent,
        presets=selector.candidate_presets,
        theory_profile=target_intent.theory_profile,
        texture_profile=target_intent.texture_profile,
        audition_id="intelligent_generation_v1",
    )

    selected_path = output_root / "selected_chordpotion_preset.json"
    selected_path.write_text(
        json.dumps(
            {
                "selector_mode": selector.selector_mode,
                "presets_considered": len(selector.candidate_presets),
                "presets_auditioned": sum(
                    1 for item in audition.candidate_results if item.transformed_midi_captured or item.wav_preview_rendered
                ),
                "selected_preset": audition.selected_preset,
                "why_selected": "highest overall_candidate_score",
                "musical_target_match": target_intent.target_pattern_family.value,
                "transformed_midi_captured": any(item.transformed_midi_captured for item in audition.candidate_results),
                "wav_rendered": False,
                "training_data_used": selector.training_data_used,
                "trained_selector_used": selector.trained_selector_used,
                "fallback_used": selector.fallback_used,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )

    transformed_captured = any(item.transformed_midi_captured for item in audition.candidate_results)
    wav_rendered = False
    fallback_used = audition.blocked_by_local_config
    blocker = audition.blocker or ""
    wav_status = "assisted_pack_created" if fallback_used else "render_failed"
    if transformed_captured:
        wav_status = "render_failed"

    (output_root / "audition_report.md").write_text((audition.output_dir / "audition_report.md").read_text(encoding="utf-8"), encoding="utf-8")
    (output_root / "generation_report.md").write_text(
        "\n".join(
            [
                "# Intelligent ChordPotion Generation Report",
                "",
                f"- selector_mode: `{selector.selector_mode}`",
                f"- presets_considered: `{len(selector.candidate_presets)}`",
                f"- presets_auditioned: `{sum(1 for item in audition.candidate_results if item.transformed_midi_captured or item.wav_preview_rendered)}`",
                f"- selected_preset: `{audition.selected_preset or 'none'}`",
                "- selection_reason: `highest overall candidate score from observed or fallback scoring`",
                f"- transformed_midi_captured: `{str(transformed_captured).lower()}`",
                f"- wav_rendered: `{str(wav_rendered).lower()}`",
                f"- training_data_used: `{str(selector.training_data_used).lower()}`",
                f"- trained_selector_used: `{str(selector.trained_selector_used).lower()}`",
                f"- fallback_used: `{str(fallback_used).lower()}`",
                f"- blocker: `{blocker or 'none'}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (output_root / "provenance_report.md").write_text(
        "\n".join(
            [
                "# Provenance Report",
                "",
                "- ChordPotion treated as black-box MIDI transformation.",
                "- No cloud execution, no raw-audio model training, no unauthorized datasets.",
                "- Preset expectations are priors only; selection depends on audition scoring.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (output_root / "review_sheet.md").write_text(
        (ROOT_DIR / "reports" / "review_queue" / "chordpotion_preset_review_template.md").read_text(encoding="utf-8")
        if (ROOT_DIR / "reports" / "review_queue" / "chordpotion_preset_review_template.md").exists()
        else "# Missing review template\n",
        encoding="utf-8",
    )
    (output_root / "wav_status.md").write_text(wav_status + "\n", encoding="utf-8")
    if transformed_captured:
        (output_root / "transformed_harmony.mid").write_bytes((ROOT_DIR / "outputs" / "chordpotion_auditions" / "intelligent_generation_v1" / "candidates" / audition.selected_preset / "transformed.mid").read_bytes())

    print(f"OUTPUT_PATH={output_root.as_posix()}")
    print(f"SELECTOR_MODE={selector.selector_mode}")
    print(f"SELECTED_PRESET={audition.selected_preset or 'none'}")
    print(f"TRANSFORMED_MIDI_CAPTURED={str(transformed_captured).lower()}")
    print(f"WAV_RENDERED={str(wav_rendered).lower()}")
    print(f"BLOCKER={blocker or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
