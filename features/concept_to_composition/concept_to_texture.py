from __future__ import annotations

from .concept_interpreter import InterpretedConcept
from .concept_schema import SongConceptBrief


def build_texture_plan(brief: SongConceptBrief, interpreted: InterpretedConcept, strategy: str) -> dict[str, object]:
    base_density = {"intro": 0.25, "verse": 0.45, "lift": 0.7, "outro": 0.5}
    if strategy == "rhythm_first":
        base_density["intro"] = 0.2
        base_density["lift"] = 0.62
    elif strategy == "weird_but_musical":
        base_density["lift"] = 0.78
        base_density["outro"] = 0.58

    return {
        "strategy": brief.texture_strategy,
        "texture_hooks_used": interpreted.texture_hooks,
        "section_density_targets": base_density,
        "vocal_space_policy": brief.vocal_space_policy,
    }
