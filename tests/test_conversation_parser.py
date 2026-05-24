from __future__ import annotations

from features.concept_to_composition.conversation_parser import parse_conversation_to_brief


def test_conversation_text_maps_to_structured_brief() -> None:
    conversation = "dark sunrise mood, sparse groove, weird but musical, preserve singable line"
    brief = parse_conversation_to_brief(conversation)
    assert brief.title
    assert brief.emotional_core
    assert brief.generation_seed >= 0
    assert "random interval jumps larger than an octave" in " ".join(brief.avoid_patterns)
