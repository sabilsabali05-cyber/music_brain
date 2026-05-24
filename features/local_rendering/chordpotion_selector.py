from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .chordpotion_intent_schema import ChordPotionTargetIntent
from .chordpotion_preset_registry import ChordPotionPresetProfile

SelectorMode = str


@dataclass
class SelectorDecision:
    selector_mode: SelectorMode
    candidate_presets: list[ChordPotionPresetProfile]
    trained_selector_used: bool
    training_data_used: bool
    fallback_used: bool


def _load_jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return len(lines)


def _load_trained_ranker(trained_ranker_path: Path | None) -> dict:
    if trained_ranker_path is None or not trained_ranker_path.exists():
        return {}
    try:
        return json.loads(trained_ranker_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def choose_selector_mode(
    audition_history_count: int,
    feedback_count: int,
    trained_ranker_available: bool,
) -> SelectorMode:
    if trained_ranker_available and audition_history_count >= 20:
        return "trained_selector"
    if feedback_count > 0:
        return "feedback_ranker_selector"
    return "heuristic_selector"


def select_candidate_presets(
    intent: ChordPotionTargetIntent,
    theory_profile: str,
    texture_profile: str,
    preset_profiles: list[ChordPotionPresetProfile],
    previous_audition_outcomes_path: Path,
    human_feedback_path: Path,
    trained_ranker_path: Path | None = None,
    top_k: int = 4,
) -> SelectorDecision:
    audition_count = _load_jsonl_count(previous_audition_outcomes_path)
    feedback_count = _load_jsonl_count(human_feedback_path)
    trained_ranker = _load_trained_ranker(trained_ranker_path)
    mode = choose_selector_mode(audition_count, feedback_count, bool(trained_ranker))

    scored: list[tuple[float, ChordPotionPresetProfile]] = []
    for preset in preset_profiles:
        score = 0.0
        if preset.expected_pattern_family == intent.target_pattern_family.value:
            score += 3.0
        score += max(0.0, 1.0 - abs(preset.expected_density - intent.target_density))
        score += max(0.0, 1.0 - abs(preset.expected_syncopation - intent.target_syncopation))
        score += max(0.0, 1.0 - abs(preset.expected_motion - intent.target_motion))
        if texture_profile and texture_profile.lower() in preset.expected_texture.lower():
            score += 1.5
        if theory_profile and theory_profile.lower() in " ".join(preset.known_good_for).lower():
            score += 1.0
        score += preset.avg_score * 0.5 + (preset.user_rating / 10.0) * 0.4
        if mode == "feedback_ranker_selector" and preset.audition_count > 0:
            score += min(1.0, preset.user_rating / 10.0)
        if mode == "trained_selector":
            model_scores = trained_ranker.get("preset_scores", {})
            score += float(model_scores.get(preset.preset_id, 0.0))
        scored.append((score, preset))

    scored.sort(key=lambda item: (-item[0], item[1].display_name.lower()))
    selected = [item[1] for item in scored[: max(1, top_k)]]
    return SelectorDecision(
        selector_mode=mode,
        candidate_presets=selected,
        trained_selector_used=mode == "trained_selector",
        training_data_used=mode in {"feedback_ranker_selector", "trained_selector"},
        fallback_used=mode == "heuristic_selector",
    )
