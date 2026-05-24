from __future__ import annotations

import hashlib
import re
from typing import Iterable

from .concept_schema import SectionPlanItem, SongConceptBrief, TempoRange


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _derive_title(conversation_text: str) -> str:
    for line in conversation_text.splitlines():
        cleaned = line.strip().lstrip("-").strip()
        if not cleaned:
            continue
        if len(cleaned) < 70:
            return cleaned.title()
    return "Song Idea 001"


def parse_conversation_to_brief(conversation_text: str) -> SongConceptBrief:
    text = conversation_text.strip()
    title = _derive_title(text)

    emotional_core = "yearning with controlled optimism"
    if _contains_any(text, ["dark", "haunt", "ghost", "night"]):
        emotional_core = "dark introspection with unresolved tension"
    elif _contains_any(text, ["joy", "sun", "bright", "uplift"]):
        emotional_core = "uplift and forward motion"

    tempo_range = TempoRange(min_bpm=88, max_bpm=108)
    if _contains_any(text, ["slow", "ballad", "floating"]):
        tempo_range = TempoRange(min_bpm=70, max_bpm=92)
    elif _contains_any(text, ["fast", "driving", "urgent"]):
        tempo_range = TempoRange(min_bpm=112, max_bpm=136)

    weirdness_policy = "controlled strangeness, melody remains human-singable"
    if _contains_any(text, ["weird", "strange", "experimental"]):
        weirdness_policy = "allow unusual harmonic turns but avoid random-note chaos"

    key_pref = "A minor / C major interchange"
    if _contains_any(text, ["major", "hopeful"]):
        key_pref = "C major with modal mixture"
    elif _contains_any(text, ["minor", "sad"]):
        key_pref = "A minor with borrowed iv and bVI"

    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)

    return SongConceptBrief(
        title=title,
        short_description="Conversation-derived concept brief for local rule-based MIDI generation.",
        emotional_core=emotional_core,
        narrative_arc="intro restraint -> emotional lift -> reflective release",
        perspective="first person interior monologue",
        scene_or_image="city lights reflected on wet pavement just before dawn",
        energy_curve=[0.25, 0.45, 0.72, 0.56],
        tension_curve=[0.35, 0.55, 0.8, 0.4],
        density_curve=[0.2, 0.42, 0.66, 0.5],
        tempo_range=tempo_range,
        key_or_mode_preference=key_pref,
        harmony_strategy="functional center with selective modal borrowing",
        chord_movement_strategy="prefer stepwise bass roots and common-tone pivots",
        bass_strategy="anchor roots on strong beats, occasional passing tones",
        melody_strategy="short singable motifs with controlled register peaks",
        rhythm_strategy="clear pocket first, syncopation as section energy rises",
        texture_strategy="sparse intro, widening mid-song, controlled release in outro",
        arrangement_strategy="4-part arc using recurring motif with variation",
        section_plan=[
            SectionPlanItem(name="intro", bars=8, intent="set scene and motif"),
            SectionPlanItem(name="verse", bars=16, intent="build story and tension"),
            SectionPlanItem(name="lift", bars=8, intent="peak harmony and rhythm identity"),
            SectionPlanItem(name="outro", bars=8, intent="resolve while keeping emotional residue"),
        ],
        motifs_to_try=["falling third", "neighbor-tone sigh", "syncopated pickup"],
        avoid_patterns=[
            "constant 16th-note clutter",
            "random interval jumps larger than an octave",
            "overlapping lead notes that remove vocal space",
        ],
        preserve_patterns=[
            "singable top line",
            "emotional chord movement continuity",
            "motif recurrence across sections",
        ],
        weirdness_policy=weirdness_policy,
        vocal_space_policy="reserve 1-3 kHz range by thinning texture during lead statements",
        reference_influence_policy="capture vibe-level influence only; no direct melodic copying",
        generation_seed=seed,
        confidence=0.74,
        unresolved_questions=[
            "Should bridge modulation be introduced in a future pass?",
            "How sparse should percussion remain in intro?",
        ],
    )


def extract_conversation_markdown_text(conversation_markdown: str) -> str:
    content = re.sub(r"```.*?```", "", conversation_markdown, flags=re.S)
    content = re.sub(r"^#+\s*", "", content, flags=re.M)
    return content.strip()
