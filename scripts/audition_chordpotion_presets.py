from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.local_rendering.chordpotion_audition import run_chordpotion_audition  # noqa: E402
from features.local_rendering.chordpotion_intent_schema import (  # noqa: E402
    ChordPotionTargetIntent,
    ChordPotionTargetPatternFamily,
)
from features.local_rendering.chordpotion_preset_registry import load_preset_profiles_from_vst_registry  # noqa: E402
from features.local_rendering.reaper_backend import load_local_render_config  # noqa: E402


def _default_intent(generation_id: str, harmony_rel: str) -> ChordPotionTargetIntent:
    return ChordPotionTargetIntent(
        intent_id="intent_default_v1",
        source_generation_id=generation_id,
        target_role="chord_pattern_generator",
        source_chord_skeleton=harmony_rel,
        target_pattern_family=ChordPotionTargetPatternFamily.ROLLING_CHORD_MOTION,
        target_density=0.45,
        target_syncopation=0.35,
        target_motion=0.55,
        target_repetition=0.45,
        target_variation=0.45,
        target_humanization=0.35,
        target_register_behavior="mid_register_movement",
        preserve_bass=True,
        preserve_top_voice=True,
        preserve_harmonic_rhythm=True,
        preserve_chord_identity=True,
        avoid_mud=True,
        avoid_random_keyboard_effect=True,
        avoid_overbusy_output=True,
        avoid_lead_conflict=True,
        desired_ear_effect="patterned harmonic motion with breathing space",
        texture_profile="warm_emotional_chord_bed",
        theory_profile="functional_harmony_voice_leading",
        confidence=0.65,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Audition ChordPotion preset candidates against target intent.")
    parser.add_argument("--generation-id", default="chordpotion_generation_v1")
    parser.add_argument("--plugin-id", default="")
    parser.add_argument("--intent-json", default="")
    parser.add_argument("--audition-id", default="")
    args = parser.parse_args()

    output_root = ROOT_DIR / "outputs" / args.generation_id
    harmony_path = output_root / "harmony_skeleton.mid"
    if not harmony_path.exists():
        raise FileNotFoundError(f"Missing harmony skeleton: {harmony_path.as_posix()}")

    local_config = load_local_render_config(ROOT_DIR / "config" / "local_render_config.local.json")
    plugin_id = args.plugin_id or str(local_config.get("preferred_chordpotion_plugin_id", "")).strip() or "chordpotion_midi_fx"
    profiles = load_preset_profiles_from_vst_registry(ROOT_DIR / "config" / "local_vst_registry.local.json", plugin_id=plugin_id)
    if not profiles:
        profiles = load_preset_profiles_from_vst_registry(ROOT_DIR / "config" / "local_vst_registry.example.json", plugin_id=plugin_id)

    if args.intent_json:
        payload = json.loads(Path(args.intent_json).read_text(encoding="utf-8"))
        intent = ChordPotionTargetIntent(
            intent_id=str(payload.get("intent_id", "intent_default_v1")),
            source_generation_id=str(payload.get("source_generation_id", args.generation_id)),
            target_role=str(payload.get("target_role", "chord_pattern_generator")),
            source_chord_skeleton=str(payload.get("source_chord_skeleton", harmony_path.relative_to(ROOT_DIR).as_posix())),
            target_pattern_family=ChordPotionTargetPatternFamily(str(payload.get("target_pattern_family", "rolling_chord_motion"))),
            target_density=float(payload.get("target_density", 0.45)),
            target_syncopation=float(payload.get("target_syncopation", 0.35)),
            target_motion=float(payload.get("target_motion", 0.55)),
            target_repetition=float(payload.get("target_repetition", 0.45)),
            target_variation=float(payload.get("target_variation", 0.45)),
            target_humanization=float(payload.get("target_humanization", 0.35)),
            target_register_behavior=str(payload.get("target_register_behavior", "mid_register_movement")),
            preserve_bass=bool(payload.get("preserve_bass", True)),
            preserve_top_voice=bool(payload.get("preserve_top_voice", True)),
            preserve_harmonic_rhythm=bool(payload.get("preserve_harmonic_rhythm", True)),
            preserve_chord_identity=bool(payload.get("preserve_chord_identity", True)),
            avoid_mud=bool(payload.get("avoid_mud", True)),
            avoid_random_keyboard_effect=bool(payload.get("avoid_random_keyboard_effect", True)),
            avoid_overbusy_output=bool(payload.get("avoid_overbusy_output", True)),
            avoid_lead_conflict=bool(payload.get("avoid_lead_conflict", True)),
            desired_ear_effect=str(payload.get("desired_ear_effect", "")),
            texture_profile=str(payload.get("texture_profile", "")),
            theory_profile=str(payload.get("theory_profile", "")),
            confidence=float(payload.get("confidence", 0.6)),
        )
    else:
        intent = _default_intent(args.generation_id, harmony_path.relative_to(ROOT_DIR).as_posix())

    audition = run_chordpotion_audition(
        repo_root=ROOT_DIR,
        harmony_skeleton_path=harmony_path,
        target_intent=intent,
        presets=profiles,
        theory_profile=intent.theory_profile,
        texture_profile=intent.texture_profile,
        audition_id=args.audition_id or None,
    )

    print(f"AUDITION_ID={audition.audition_id}")
    print(f"OUTPUT_PATH={audition.output_dir.as_posix()}")
    print(f"PRESETS_CONSIDERED={len(profiles)}")
    auditioned = sum(1 for row in audition.candidate_results if row.transformed_midi_captured or row.wav_preview_rendered)
    print(f"PRESETS_AUDITIONED={auditioned}")
    print(f"SELECTED_PRESET={audition.selected_preset or 'none'}")
    print(f"BLOCKED={str(audition.blocked_by_local_config).lower()}")
    print(f"BLOCKER={audition.blocker or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
