from __future__ import annotations

from dataclasses import dataclass

from .concept_schema import SongConceptBrief


@dataclass(slots=True)
class InterpretedConcept:
    emotional_goals: list[str]
    theory_hooks: list[str]
    rhythm_hooks: list[str]
    texture_hooks: list[str]
    avoid_patterns: list[str]
    preserve_patterns: list[str]
    key_center: str
    weirdness_budget: float


def interpret_concept_language(brief: SongConceptBrief) -> InterpretedConcept:
    emotion = brief.emotional_core.lower()
    emotional_goals = ["maintain continuity", "support narrative arc"]
    theory_hooks = ["stepwise chord roots", "common-tone voice-leading"]
    rhythm_hooks = ["clear downbeat anchors", "syncopation in lift sections"]
    texture_hooks = ["dynamic layer growth", "vocal-space aware arrangement"]
    weirdness_budget = 0.2

    if "dark" in emotion or "tension" in emotion:
        theory_hooks.extend(["borrowed bVI color", "suspended cadential delays"])
        rhythm_hooks.append("leave negative space for unease")
        texture_hooks.append("narrow-band pads in intro")
        weirdness_budget = 0.35
    if "uplift" in emotion or "optimism" in emotion:
        theory_hooks.append("major add9 release voicings")
        rhythm_hooks.append("late-beat pickups into cadences")
        texture_hooks.append("wider upper harmonics in final section")
        weirdness_budget = max(weirdness_budget, 0.25)

    if "no random-note chaos" in brief.weirdness_policy.lower():
        weirdness_budget = min(weirdness_budget, 0.4)

    return InterpretedConcept(
        emotional_goals=emotional_goals,
        theory_hooks=theory_hooks,
        rhythm_hooks=rhythm_hooks,
        texture_hooks=texture_hooks,
        avoid_patterns=brief.avoid_patterns,
        preserve_patterns=brief.preserve_patterns,
        key_center=brief.key_or_mode_preference,
        weirdness_budget=weirdness_budget,
    )
