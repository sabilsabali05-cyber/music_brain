from __future__ import annotations

from typing import Any


RHYTHM_LEXICON: list[dict[str, Any]] = [
    {
        "pattern_id": "tresillo_3_3_2",
        "family": "tresillo_3_3_2",
        "meter_contexts": ["4/4", "2/4"],
        "token_patterns": ["x..x..x.", "x..x..x..", "x..x..x..."],
        "interval_ratios": [[1.5, 1.5, 1.0], [3.0, 3.0, 2.0]],
        "accent_patterns": ["X..x..x."],
        "rotation_invariant": True,
        "subdivision_context": "8th",
        "related_patterns": ["habanera", "dembow_like"],
        "rhythm_concepts": ["timeline", "cycle", "motif", "repetition"],
        "philosophy_sources": ["timeline", "geometry", "cycle"],
        "detection_targets": ["asymmetrical_skeleton", "token_pattern", "rotation_equivalence"],
        "notes": "Canonical 3-3-2 asymmetrical cell.",
        "limitations": "Token-only matching cannot capture full ensemble context.",
    },
    {
        "pattern_id": "habanera",
        "family": "habanera",
        "meter_contexts": ["4/4"],
        "token_patterns": ["x..xx.x.", "X..xx.x."],
        "interval_ratios": [[1.5, 0.5, 1.0, 1.0]],
        "accent_patterns": ["X..xX.x."],
        "rotation_invariant": False,
        "subdivision_context": "8th",
        "related_patterns": ["tresillo_3_3_2", "dembow_like"],
        "rhythm_concepts": ["timeline", "gesture", "motif"],
        "philosophy_sources": ["timeline", "gesture"],
        "detection_targets": ["offbeat_anchor", "token_pattern", "accent_pattern"],
        "notes": "Habanera-like long-short profile.",
        "limitations": "Can be confused with ornamented tresillo variants.",
    },
    {
        "pattern_id": "cinquillo",
        "family": "cinquillo",
        "meter_contexts": ["2/4", "4/4"],
        "token_patterns": ["x.x.x..x.", "x.x.x..x.."],
        "interval_ratios": [[1.0, 1.0, 1.0, 2.0, 1.0]],
        "accent_patterns": ["X.x.x..x."],
        "rotation_invariant": True,
        "subdivision_context": "8th",
        "related_patterns": ["habanera"],
        "rhythm_concepts": ["timeline", "geometry", "motif"],
        "philosophy_sources": ["timeline", "geometry"],
        "detection_targets": ["asymmetrical_skeleton", "evenness_score"],
        "notes": "Five-onset asymmetrical pattern.",
        "limitations": "Dense textures may collapse this into generic syncopation.",
    },
    {
        "pattern_id": "son_clave_3_2",
        "family": "clave",
        "meter_contexts": ["4/4"],
        "token_patterns": ["x..x...x..x.x..."],
        "interval_ratios": [[3.0, 3.0, 4.0, 2.0, 4.0]],
        "accent_patterns": ["X..x...X..x.x..."],
        "rotation_invariant": False,
        "subdivision_context": "8th",
        "related_patterns": ["son_clave_2_3", "rumba_clave_3_2"],
        "rhythm_concepts": ["timeline", "cycle", "return"],
        "philosophy_sources": ["timeline", "cycle"],
        "detection_targets": ["timeline_fit", "asymmetrical_skeleton", "return_point"],
        "notes": "Son clave 3-2 orientation.",
        "limitations": "Requires longer phrase window to disambiguate orientation.",
    },
    {
        "pattern_id": "son_clave_2_3",
        "family": "clave",
        "meter_contexts": ["4/4"],
        "token_patterns": ["x.x...x..x...x.."],
        "interval_ratios": [[2.0, 4.0, 3.0, 3.0, 4.0]],
        "accent_patterns": ["X.x...x..X...x.."],
        "rotation_invariant": False,
        "subdivision_context": "8th",
        "related_patterns": ["son_clave_3_2", "rumba_clave_2_3"],
        "rhythm_concepts": ["timeline", "cycle", "return"],
        "philosophy_sources": ["timeline", "cycle"],
        "detection_targets": ["timeline_fit", "asymmetrical_skeleton", "return_point"],
        "notes": "Son clave 2-3 orientation.",
        "limitations": "Orientation can flip under phrase offset.",
    },
    {
        "pattern_id": "rumba_clave_3_2",
        "family": "clave",
        "meter_contexts": ["4/4"],
        "token_patterns": ["x..x...x.x...x.."],
        "interval_ratios": [[3.0, 3.0, 2.0, 4.0, 4.0]],
        "accent_patterns": ["X..x...x.X...x.."],
        "rotation_invariant": False,
        "subdivision_context": "8th",
        "related_patterns": ["rumba_clave_2_3", "son_clave_3_2"],
        "rhythm_concepts": ["timeline", "cycle", "syncopation"],
        "philosophy_sources": ["timeline", "cross_rhythm"],
        "detection_targets": ["timeline_fit", "offbeat_anchor", "phase_tension"],
        "notes": "Rumba clave 3-2 profile.",
        "limitations": "Microtiming feel is not represented in symbols.",
    },
    {
        "pattern_id": "rumba_clave_2_3",
        "family": "clave",
        "meter_contexts": ["4/4"],
        "token_patterns": ["x...x..x...x.x.."],
        "interval_ratios": [[4.0, 3.0, 4.0, 2.0, 3.0]],
        "accent_patterns": ["X...x..x...X.x.."],
        "rotation_invariant": False,
        "subdivision_context": "8th",
        "related_patterns": ["rumba_clave_3_2", "son_clave_2_3"],
        "rhythm_concepts": ["timeline", "cycle", "syncopation"],
        "philosophy_sources": ["timeline", "cross_rhythm"],
        "detection_targets": ["timeline_fit", "offbeat_anchor", "phase_tension"],
        "notes": "Rumba clave 2-3 profile.",
        "limitations": "Phrase boundary errors can mimic opposite orientation.",
    },
    {
        "pattern_id": "backbeat_2_4",
        "family": "backbeat",
        "meter_contexts": ["4/4"],
        "token_patterns": ["x...x...x...x...", ".x..X...x...X..."],
        "interval_ratios": [[1.0, 1.0, 1.0, 1.0]],
        "accent_patterns": [".x..X...x...X..."],
        "rotation_invariant": True,
        "subdivision_context": "16th",
        "related_patterns": ["boom_bap_backbeat", "gospel_clap_backbeat"],
        "rhythm_concepts": ["meter", "groove", "entrainment"],
        "philosophy_sources": ["attention", "gesture"],
        "detection_targets": ["beat_alignment", "entrainment_strength", "accent_pattern"],
        "notes": "Generic backbeat emphasis on beats 2 and 4.",
        "limitations": "Cannot identify instrumentation role.",
    },
    {
        "pattern_id": "four_on_the_floor",
        "family": "four_on_the_floor",
        "meter_contexts": ["4/4"],
        "token_patterns": ["x...x...x...x..."],
        "interval_ratios": [[1.0, 1.0, 1.0, 1.0]],
        "accent_patterns": ["X...X...X...X..."],
        "rotation_invariant": True,
        "subdivision_context": "16th",
        "related_patterns": ["march_duple"],
        "rhythm_concepts": ["pulse", "meter", "eurhythmia"],
        "philosophy_sources": ["attention", "hierarchy"],
        "detection_targets": ["pulse_confidence", "grid_stability"],
        "notes": "Strong quarter-note regular pulse.",
        "limitations": "May overmatch dense metronomic regions.",
    },
    {
        "pattern_id": "waltz_3_4",
        "family": "waltz_3_4",
        "meter_contexts": ["3/4", "6/8"],
        "token_patterns": ["x..x..x..", "X..x..x.."],
        "interval_ratios": [[1.0, 1.0, 1.0]],
        "accent_patterns": ["X..x..x.."],
        "rotation_invariant": True,
        "subdivision_context": "8th",
        "related_patterns": ["march_duple"],
        "rhythm_concepts": ["meter", "hierarchy", "cycle"],
        "philosophy_sources": ["hierarchy", "cycle"],
        "detection_targets": ["beat_grouping", "meter_consistency"],
        "notes": "Three-beat grouping candidate.",
        "limitations": "Needs bar-level framing for certainty.",
    },
    {
        "pattern_id": "march_duple",
        "family": "march_duple",
        "meter_contexts": ["2/4", "4/4"],
        "token_patterns": ["x.x.x.x.", "X.x.X.x."],
        "interval_ratios": [[1.0, 1.0, 1.0, 1.0]],
        "accent_patterns": ["X.x.X.x."],
        "rotation_invariant": True,
        "subdivision_context": "8th",
        "related_patterns": ["four_on_the_floor", "backbeat_2_4"],
        "rhythm_concepts": ["meter", "pulse", "eurhythmia"],
        "philosophy_sources": ["hierarchy", "attention"],
        "detection_targets": ["beat_grouping", "pulse_confidence"],
        "notes": "Duple march-like regularity.",
        "limitations": "Insensitive to swing feel or rubato.",
    },
    {
        "pattern_id": "swing_shuffle",
        "family": "shuffle",
        "meter_contexts": ["4/4", "12/8"],
        "token_patterns": ["x..x..x..x..", "X..x..X..x.."],
        "interval_ratios": [[2.0, 1.0, 2.0, 1.0], [0.667, 0.333, 0.667, 0.333]],
        "accent_patterns": ["X..x..X..x.."],
        "rotation_invariant": True,
        "subdivision_context": "triplet",
        "related_patterns": ["twelve_eight_gospel"],
        "rhythm_concepts": ["meter", "groove", "gesture"],
        "philosophy_sources": ["attention", "gesture"],
        "detection_targets": ["subdivision_family", "microtiming_shape", "accent_pattern"],
        "notes": "Long-short swing/shuffle subdivision.",
        "limitations": "True swing microtiming is approximated.",
    },
    {
        "pattern_id": "twelve_eight_gospel",
        "family": "twelve_eight_gospel",
        "meter_contexts": ["12/8"],
        "token_patterns": ["x..x..x..x..", "x..x.x..x..x"],
        "interval_ratios": [[3.0, 3.0, 3.0, 3.0], [2.0, 1.0, 3.0, 2.0, 1.0, 3.0]],
        "accent_patterns": ["X..x..X..x.."],
        "rotation_invariant": True,
        "subdivision_context": "triplet",
        "related_patterns": ["gospel_clap_backbeat", "swing_shuffle"],
        "rhythm_concepts": ["meter", "social_ritual", "groove"],
        "philosophy_sources": ["everyday_life", "attention", "gesture"],
        "detection_targets": ["subdivision_family", "collective_arrival", "entrainment_strength"],
        "notes": "12/8 gospel groove candidate.",
        "limitations": "Genre attribution is heuristic and context-dependent.",
    },
    {
        "pattern_id": "gospel_clap_backbeat",
        "family": "gospel_clap_backbeat",
        "meter_contexts": ["4/4", "12/8"],
        "token_patterns": [".x..X...x...X...", ".x..X..x.x..X..."],
        "interval_ratios": [[1.0, 1.0, 1.0, 1.0]],
        "accent_patterns": [".x..X...x...X..."],
        "rotation_invariant": True,
        "subdivision_context": "16th",
        "related_patterns": ["backbeat_2_4", "twelve_eight_gospel"],
        "rhythm_concepts": ["groove", "social_ritual", "entrainment"],
        "philosophy_sources": ["everyday_life", "attention"],
        "detection_targets": ["collective_arrival", "accent_pattern", "entrainment_strength"],
        "notes": "Clap-emphasized backbeat behavior.",
        "limitations": "Requires accent quality evidence; tokens alone are weak.",
    },
    {
        "pattern_id": "boom_bap_backbeat",
        "family": "boom_bap_backbeat",
        "meter_contexts": ["4/4"],
        "token_patterns": ["x...X...x...X...", "x...X..x.x..X..."],
        "interval_ratios": [[1.0, 1.0, 1.0, 1.0]],
        "accent_patterns": ["X...x...X...x..."],
        "rotation_invariant": False,
        "subdivision_context": "16th",
        "related_patterns": ["backbeat_2_4", "amen_break_like"],
        "rhythm_concepts": ["groove", "meter", "gesture"],
        "philosophy_sources": ["gesture", "attention"],
        "detection_targets": ["accent_pattern", "beat_alignment", "entrainment_strength"],
        "notes": "Boom-bap-like kick/snare alternation.",
        "limitations": "Instrument assignment unknown; only rhythmic proxy.",
    },
    {
        "pattern_id": "trap_hihat_subdivision",
        "family": "trap_subdivision",
        "meter_contexts": ["4/4"],
        "token_patterns": ["x.x.x.x.x.x.x.x.", "x.xxx.x.xxx.x.x."],
        "interval_ratios": [[0.5, 0.5, 0.5, 0.5], [1.0, 0.5, 0.5, 1.0]],
        "accent_patterns": ["x.X.x.X.x.X.x.X."],
        "rotation_invariant": True,
        "subdivision_context": "16th/32nd",
        "related_patterns": ["boom_bap_backbeat"],
        "rhythm_concepts": ["density", "gesture", "groove"],
        "philosophy_sources": ["gesture", "attention"],
        "detection_targets": ["subdivision_family", "burst_density", "accent_pattern"],
        "notes": "Fast subdivision and rolls candidate.",
        "limitations": "May confuse with any dense percussion texture.",
    },
    {
        "pattern_id": "dembow_like",
        "family": "dembow_like",
        "meter_contexts": ["4/4"],
        "token_patterns": ["x..x...x..x.x...", "x..x..x.x..x..."],
        "interval_ratios": [[3.0, 4.0, 3.0, 2.0, 4.0]],
        "accent_patterns": ["X..x...x..X.x..."],
        "rotation_invariant": True,
        "subdivision_context": "8th/16th",
        "related_patterns": ["tresillo_3_3_2", "habanera"],
        "rhythm_concepts": ["timeline", "cycle", "social_ritual"],
        "philosophy_sources": ["timeline", "everyday_life"],
        "detection_targets": ["asymmetrical_skeleton", "collective_arrival", "loop_persistence"],
        "notes": "Dembow-like asymmetrical loop candidate.",
        "limitations": "Broad family label; many sub-variants.",
    },
    {
        "pattern_id": "bossa_like",
        "family": "bossa_like",
        "meter_contexts": ["4/4"],
        "token_patterns": ["x..x.x...x.x...."],
        "interval_ratios": [[3.0, 2.0, 4.0, 2.0, 5.0]],
        "accent_patterns": ["X..x.x...x.X...."],
        "rotation_invariant": True,
        "subdivision_context": "16th",
        "related_patterns": ["samba_like"],
        "rhythm_concepts": ["timeline", "gesture", "groove"],
        "philosophy_sources": ["gesture", "timeline"],
        "detection_targets": ["asymmetrical_skeleton", "offbeat_anchor", "accent_pattern"],
        "notes": "Bossa-like syncopated comping contour.",
        "limitations": "Needs harmonic/instrument evidence for strong claim.",
    },
    {
        "pattern_id": "samba_like",
        "family": "samba_like",
        "meter_contexts": ["2/4", "4/4"],
        "token_patterns": ["x.x..x.x..x.x..", "x..x.x.x..x.x.."],
        "interval_ratios": [[1.0, 2.0, 1.0, 2.0, 1.0]],
        "accent_patterns": ["X.x..x.X..x.x.."],
        "rotation_invariant": True,
        "subdivision_context": "16th",
        "related_patterns": ["bossa_like", "son_clave_2_3"],
        "rhythm_concepts": ["timeline", "polyrhythm", "groove"],
        "philosophy_sources": ["cross_rhythm", "timeline"],
        "detection_targets": ["multi_grid_fit", "offbeat_anchor", "accent_pattern"],
        "notes": "Samba-like interlocking candidate.",
        "limitations": "Interlocking parts are collapsed in mono token view.",
    },
    {
        "pattern_id": "amen_break_like",
        "family": "amen_break_like",
        "meter_contexts": ["4/4"],
        "token_patterns": ["x..x.X..x.x.X..", "x.x.X...x.x.X..."],
        "interval_ratios": [[2.0, 2.0, 1.0, 1.0, 2.0]],
        "accent_patterns": ["X..x.X..x.x.X.."],
        "rotation_invariant": False,
        "subdivision_context": "16th",
        "related_patterns": ["boom_bap_backbeat", "trap_hihat_subdivision"],
        "rhythm_concepts": ["gesture", "density", "groove"],
        "philosophy_sources": ["gesture", "attention"],
        "detection_targets": ["burst_density", "accent_pattern", "phase_tension"],
        "notes": "Amen-break-like breakbeat contour candidate.",
        "limitations": "Many breakbeat variants can trigger false positives.",
    },
    {
        "pattern_id": "generic_vamp_cycle",
        "family": "generic_vamp_cycle",
        "meter_contexts": ["4/4", "12/8", "free"],
        "token_patterns": ["x...x...x...x...", "x..x..x..x.."],
        "interval_ratios": [[1.0, 1.0, 1.0, 1.0]],
        "accent_patterns": ["X...x...X...x..."],
        "rotation_invariant": True,
        "subdivision_context": "any",
        "related_patterns": ["repeated_chord_vamp_candidate", "twelve_eight_gospel"],
        "rhythm_concepts": ["cycle", "repetition", "harmonic_rhythm", "return"],
        "philosophy_sources": ["cycle", "hierarchy", "everyday_life"],
        "detection_targets": ["loop_persistence", "cyclic_return", "harmonic_loop"],
        "notes": "Generic repeated cycle when specific family is uncertain.",
        "limitations": "Very broad fallback label.",
    },
    {
        "pattern_id": "sparse_call_response",
        "family": "sparse_call_response",
        "meter_contexts": ["4/4", "free"],
        "token_patterns": ["x... ...x... ...", "x....x...."],
        "interval_ratios": [[2.0, 2.0], [3.0, 3.0]],
        "accent_patterns": ["X... ...x... ..."],
        "rotation_invariant": True,
        "subdivision_context": "any",
        "related_patterns": ["generic_vamp_cycle"],
        "rhythm_concepts": ["call_response", "density", "hierarchy"],
        "philosophy_sources": ["everyday_life", "hierarchy"],
        "detection_targets": ["alternating_density", "phrase_response_gap", "sparse_dense_exchange"],
        "notes": "Sparse alternating call/response candidate.",
        "limitations": "Requires phrase segmentation context for strong confidence.",
    },
]


def normalize_token_pattern(pattern: str) -> str:
    text = str(pattern or "").replace(" ", "")
    allowed = []
    for ch in text:
        if ch in {"x", "X"}:
            allowed.append("x")
        elif ch == ".":
            allowed.append(".")
    return "".join(allowed)


def rotate_pattern(pattern: str, n: int) -> str:
    text = str(pattern or "")
    if not text:
        return text
    shift = n % len(text)
    return text[shift:] + text[:shift]


def _onset_positions(pattern: str) -> set[int]:
    text = normalize_token_pattern(pattern)
    return {idx for idx, ch in enumerate(text) if ch == "x"}


def token_similarity(a: str, b: str) -> float:
    aa = normalize_token_pattern(a)
    bb = normalize_token_pattern(b)
    if not aa or not bb:
        return 0.0
    pos_a = _onset_positions(aa)
    pos_b = _onset_positions(bb)
    if not pos_a and not pos_b:
        return 1.0
    union = len(pos_a | pos_b)
    if union == 0:
        return 0.0
    return round(len(pos_a & pos_b) / union, 6)


def ratio_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    width = min(len(a), len(b))
    if width == 0:
        return 0.0
    error = 0.0
    for idx in range(width):
        av = float(a[idx])
        bv = float(b[idx])
        error += min(1.0, abs(av - bv) / max(0.001, abs(bv)))
    return round(max(0.0, 1.0 - (error / width)), 6)


def accent_similarity(a: str, b: str) -> float:
    def _accent_positions(text: str) -> set[int]:
        return {idx for idx, ch in enumerate(str(text or "").replace(" ", "")) if ch == "X"}

    pos_a = _accent_positions(a)
    pos_b = _accent_positions(b)
    if not pos_a and not pos_b:
        return 0.0
    union = len(pos_a | pos_b)
    if union == 0:
        return 0.0
    return round(len(pos_a & pos_b) / union, 6)


def _best_token_similarity(candidate: str, lex_item: dict[str, Any]) -> tuple[float, str]:
    best = 0.0
    best_pattern = ""
    normalized = normalize_token_pattern(candidate)
    patterns = lex_item.get("token_patterns", [])
    if not isinstance(patterns, list):
        return 0.0, ""
    for pat in patterns:
        target = normalize_token_pattern(str(pat))
        if not target:
            continue
        checks = [target]
        if bool(lex_item.get("rotation_invariant")):
            checks = [rotate_pattern(target, idx) for idx in range(len(target))]
        for check in checks:
            score = token_similarity(normalized, check)
            if score > best:
                best = score
                best_pattern = str(pat)
    return best, best_pattern


def classify_rhythm_pattern(motif_or_region: dict[str, Any]) -> dict[str, Any]:
    token_pattern = normalize_token_pattern(str(motif_or_region.get("token_pattern", "")))
    accent_pattern = str(motif_or_region.get("accent_pattern", ""))
    ratio_pattern = motif_or_region.get("normalized_ratio_pattern", [])
    if not isinstance(ratio_pattern, list):
        ratio_pattern = []
    best: dict[str, Any] | None = None
    for item in RHYTHM_LEXICON:
        token_score, matched_pattern = _best_token_similarity(token_pattern, item)
        accent_score = 0.0
        accents = item.get("accent_patterns", [])
        if isinstance(accents, list) and accents:
            accent_score = max(accent_similarity(accent_pattern, str(value)) for value in accents)
        ratio_score = 0.0
        ratios = item.get("interval_ratios", [])
        if isinstance(ratios, list) and ratios and ratio_pattern:
            ratio_score = max(ratio_similarity([float(v) for v in ratio_pattern], [float(x) for x in value]) for value in ratios if isinstance(value, list))
        confidence = (0.65 * token_score) + (0.2 * accent_score) + (0.15 * ratio_score)
        if token_pattern and set(token_pattern) == {"x"} and item["family"] in {"clave", "tresillo_3_3_2"}:
            confidence *= 0.55
        result = {
            "matched_pattern_id": item["pattern_id"],
            "matched_family": item["family"],
            "confidence": round(float(confidence), 6),
            "similarity_breakdown": {
                "token_similarity": round(float(token_score), 6),
                "accent_similarity": round(float(accent_score), 6),
                "ratio_similarity": round(float(ratio_score), 6),
            },
            "evidence": {
                "token_pattern": token_pattern,
                "matched_token_pattern": matched_pattern,
                "accent_pattern": accent_pattern,
            },
            "rhythm_concepts": list(item.get("rhythm_concepts", [])),
            "philosophy_sources": list(item.get("philosophy_sources", [])),
            "detection_targets": list(item.get("detection_targets", [])),
            "limitations": [str(item.get("limitations", "")), "lexicon matching is heuristic and symbolic."],
        }
        if best is None or float(result["confidence"]) > float(best["confidence"]):
            best = result
    if best is None:
        return {
            "matched_pattern_id": "unclassified",
            "matched_family": "unknown",
            "confidence": 0.0,
            "similarity_breakdown": {"token_similarity": 0.0, "accent_similarity": 0.0, "ratio_similarity": 0.0},
            "evidence": {"token_pattern": token_pattern},
            "rhythm_concepts": ["motif"],
            "philosophy_sources": ["geometry"],
            "detection_targets": ["token_pattern"],
            "limitations": ["no lexicon candidates available for comparison."],
        }
    return best


def classify_rhythm_patterns(motifs_or_regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in motifs_or_regions:
        if not isinstance(item, dict):
            continue
        output.append(classify_rhythm_pattern(item))
    return output
