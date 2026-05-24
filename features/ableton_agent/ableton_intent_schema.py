from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AbletonIntent:
    intent_id: str
    prompt: str
    goal: str
    preferred_sections: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    generated_candidates_requested: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "prompt": self.prompt,
            "goal": self.goal,
            "preferred_sections": list(self.preferred_sections),
            "constraints": list(self.constraints),
            "generated_candidates_requested": list(self.generated_candidates_requested),
            "notes": self.notes,
        }


ABLETON_INTENT_EXAMPLES: list[dict[str, Any]] = [
    {
        "intent_id": "intent_01_bridge_lift",
        "prompt": "Add an 8-bar bridge that lifts energy without changing the verse groove.",
        "goal": "Create contrast before final chorus.",
        "preferred_sections": ["bridge", "pre-chorus"],
        "constraints": ["Preserve existing chorus clips", "Keep arrangement human-reviewable"],
        "generated_candidates_requested": ["bridge_candidate_a", "bridge_candidate_b"],
        "notes": "Candidate material is a suggestion, not final output.",
    },
    {
        "intent_id": "intent_02_transition_support",
        "prompt": "Build a transition from intro into verse with a short riser and drum fill.",
        "goal": "Improve section handoff.",
        "preferred_sections": ["intro", "verse"],
        "constraints": ["No audio rendering", "No automatic Live Set writes"],
        "generated_candidates_requested": ["transition_fill_candidate"],
        "notes": "Keep source-separated evidence marked witness_not_truth.",
    },
    {
        "intent_id": "intent_03_arrangement_thinning",
        "prompt": "Thin dense layers in the second chorus to make room for lead.",
        "goal": "Reduce density while preserving hook.",
        "preferred_sections": ["chorus_2"],
        "constraints": ["All destructive edits require review"],
        "generated_candidates_requested": [],
        "notes": "Focus on muting or moving clips in planning only.",
    },
    {
        "intent_id": "intent_04_variation_insert",
        "prompt": "Insert a generated variation for the bass clip in the bridge.",
        "goal": "Increase melodic novelty in bridge.",
        "preferred_sections": ["bridge"],
        "constraints": ["Generated clip must include provenance", "Keep dry-run default"],
        "generated_candidates_requested": ["bass_variation_candidate_v3"],
        "notes": "Mark model output as generated_candidate.",
    },
    {
        "intent_id": "intent_05_balance_mix",
        "prompt": "Lower pad track volume and pan arps slightly right for clarity.",
        "goal": "Open midrange for vocals.",
        "preferred_sections": ["verse", "chorus"],
        "constraints": ["Clamp automation values to valid ranges"],
        "generated_candidates_requested": [],
        "notes": "Unknown devices should warn, not fake success.",
    },
    {
        "intent_id": "intent_06_scene_plan",
        "prompt": "Create scenes for intro, verse, chorus, and bridge rehearsal snapshots.",
        "goal": "Organize arrangement review checkpoints.",
        "preferred_sections": ["intro", "verse", "chorus", "bridge"],
        "constraints": ["No Ableton connection required"],
        "generated_candidates_requested": [],
        "notes": "Plan scene labels only; no launch automation.",
    },
    {
        "intent_id": "intent_07_export_review",
        "prompt": "Prepare an export review package with command preview and risk checklist.",
        "goal": "Hand off decisions for human approval.",
        "preferred_sections": ["full_song"],
        "constraints": ["No GUI automation", "No real execution"],
        "generated_candidates_requested": [],
        "notes": "Reports must avoid private local paths.",
    },
]
