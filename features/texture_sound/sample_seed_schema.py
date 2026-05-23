from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, TypedDict

AssetTypeName = Literal[
    "drum_break",
    "drum_loop",
    "percussion_loop",
    "drum_one_shot",
    "synth_one_shot",
    "bass_one_shot",
    "chord_stab",
    "vocal_chop",
    "texture",
    "drone",
    "fx",
    "riser",
    "field_recording",
    "full_phrase",
    "unknown",
]

SampleRoleName = Literal[
    "bass",
    "lead",
    "pad",
    "pluck",
    "percussion",
    "fx",
    "riser",
    "choir_like",
    "texture_bed",
    "drone",
    "counter_melody",
    "unknown",
    "rhythm_source",
    "groove_reference",
    "slicing_candidate",
    "transition",
    "pure_data_granular_source_candidate",
    "synplant_seed_candidate",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SampleRoleCandidate(TypedDict):
    role: SampleRoleName
    confidence: float
    evidence: list[str]
    is_heuristic: bool


class SampleSeedFeatureProfile(TypedDict):
    duration_seconds: float | None
    sample_rate: int | None
    channels: int | None
    format: str | None
    feature_status: str
    analysis_refs: list[str]
    limitations: list[str]


class SampleSearchQuery(TypedDict):
    query_id: str
    requested_roles: list[SampleRoleName]
    requested_asset_types: list[AssetTypeName]
    intended_use: str
    created_at: str


class SampleSearchResult(TypedDict):
    query_id: str
    sample_id: str
    score: float
    reasons: list[str]
    selected_for_review: bool


class SynplantSeedCandidate(TypedDict):
    sample_id: str
    eligibility: Literal["eligible", "review_required", "ineligible"]
    confidence: float
    rationale: list[str]


class SampleSeedRecord(TypedDict):
    sample_id: str
    library_id: str
    source_path: str
    relative_path: str
    filename: str
    extension: str
    file_size_bytes: int
    file_hash_sha256: str | None
    duration_seconds: float | None
    sample_rate: int | None
    channels: int | None
    format: str | None
    authorization_status: str
    review_status: str
    intended_uses: list[str]
    role_candidates: list[SampleRoleCandidate]
    texture_tags: list[str]
    feature_status: str
    analysis_refs: list[str]
    limitations: list[str]
    asset_type_guess: AssetTypeName
    asset_type_confidence: float
    asset_type_evidence: list[str]
    needs_human_review: bool
    source_type: str
    ingestion_context: str
    asset_type_is_heuristic: bool
    classification_method: str


class SampleLibraryManifest(TypedDict):
    library_id: str
    root_path: str
    source_type: str
    authorization_status: str
    intended_uses: list[str]
    generated_at: str
    file_counts: dict[str, int]
    records_path: str
    report_json_path: str
    report_markdown_path: str
    indexing_policy: dict[str, bool]


class SampleLibraryIndexReport(TypedDict):
    library_id: str
    source_type: str
    root_path: str
    generated_at: str
    files_scanned: int
    supported_files_indexed: int
    unsupported_files_skipped: int
    unreadable_or_problem_files: int
    unsupported_files: list[str]
    unreadable_files: list[str]
    notes: list[str]


def classify_asset_type_guess(
    *,
    relative_path: str,
    filename: str,
    duration_seconds: float | None,
) -> tuple[AssetTypeName, float, list[str], bool]:
    path_hint = f"{relative_path} {filename}".lower()
    evidence: list[str] = []
    is_short = duration_seconds is not None and duration_seconds <= 2.0
    is_longer = duration_seconds is not None and duration_seconds > 2.0

    def _match(*tokens: str) -> bool:
        return any(token in path_hint for token in tokens)

    if is_short and _match("kick", "snare", "hat", "hihat", "clap", "rim", "tom"):
        evidence.append("short_duration_and_drum_hit_keywords")
        return "drum_one_shot", 0.7, evidence, False
    if is_short and _match("bass", "sub", "808"):
        evidence.append("short_duration_and_bass_keywords")
        return "bass_one_shot", 0.62, evidence, False
    if is_short and _match("stab", "chord", "chrd"):
        evidence.append("short_duration_and_chord_stab_keywords")
        return "chord_stab", 0.62, evidence, False
    if is_short and _match("vox", "vocal", "chop"):
        evidence.append("short_duration_and_vocal_chop_keywords")
        return "vocal_chop", 0.62, evidence, False
    if is_short and _match("synth", "lead", "pluck", "arp", "keys"):
        evidence.append("short_duration_and_synth_keywords")
        return "synth_one_shot", 0.64, evidence, False
    if is_longer and _match("breakbeat", "drum break", "drumbreak", "amen break", "break"):
        evidence.append("loop_length_and_break_keywords")
        return "drum_break", 0.68, evidence, False
    if is_longer and _match("drum loop", "drumloop", "beat loop"):
        evidence.append("loop_length_and_drum_loop_keywords")
        return "drum_loop", 0.66, evidence, False
    if is_longer and _match("perc loop", "percussion loop", "shaker loop"):
        evidence.append("loop_length_and_percussion_loop_keywords")
        return "percussion_loop", 0.64, evidence, False
    if _match("riser", "sweep up", "sweep", "uplifter"):
        evidence.append("riser_keywords")
        return "riser", 0.6, evidence, False
    if _match("impact", "boom", "hit fx", "whoosh", "fx"):
        evidence.append("fx_keywords")
        return "fx", 0.58, evidence, False
    if _match("drone", "sustain"):
        evidence.append("drone_keywords")
        return "drone", 0.58, evidence, False
    if _match("texture", "ambient", "ambience", "atmo", "atmos", "pad"):
        evidence.append("texture_keywords")
        return "texture", 0.56, evidence, False
    if _match("field", "foley", "location", "recording"):
        evidence.append("field_recording_keywords")
        return "field_recording", 0.56, evidence, False
    if is_longer and _match("phrase", "melody", "riff", "vocal phrase"):
        evidence.append("longer_duration_phrase_keywords")
        return "full_phrase", 0.55, evidence, False

    if duration_seconds is not None:
        evidence.append(f"duration_seconds={duration_seconds:.3f}_insufficient_for_confident_class")
    else:
        evidence.append("duration_unknown")
    evidence.append("filename_path_hints_inconclusive")
    return "unknown", 0.25, evidence, True


def default_role_candidates_for_asset(asset_type: AssetTypeName) -> list[SampleRoleCandidate]:
    mapping: dict[AssetTypeName, list[SampleRoleName]] = {
        "drum_break": ["rhythm_source", "groove_reference", "slicing_candidate"],
        "drum_loop": ["rhythm_source", "groove_reference", "slicing_candidate"],
        "percussion_loop": ["rhythm_source", "groove_reference", "slicing_candidate"],
        "drum_one_shot": ["percussion"],
        "synth_one_shot": ["synplant_seed_candidate"],
        "bass_one_shot": ["synplant_seed_candidate", "bass"],
        "chord_stab": ["synplant_seed_candidate", "pad", "pluck"],
        "vocal_chop": ["synplant_seed_candidate", "counter_melody"],
        "texture": ["texture_bed", "transition", "pure_data_granular_source_candidate"],
        "drone": ["drone", "texture_bed", "pure_data_granular_source_candidate"],
        "fx": ["fx", "transition", "pure_data_granular_source_candidate"],
        "riser": ["riser", "transition", "pure_data_granular_source_candidate"],
        "field_recording": ["texture_bed", "transition", "pure_data_granular_source_candidate"],
        "full_phrase": ["counter_melody", "slicing_candidate"],
        "unknown": ["unknown"],
    }
    roles = mapping.get(asset_type, ["unknown"])
    return [
        {
            "role": role,
            "confidence": 0.55 if role != "unknown" else 0.2,
            "evidence": [f"asset_type_rule:{asset_type}"],
            "is_heuristic": True,
        }
        for role in roles
    ]


def derive_usage_policy(asset_type: AssetTypeName) -> SynplantSeedCandidate:
    synplant_seed_assets = {"synth_one_shot", "bass_one_shot", "chord_stab", "vocal_chop"}
    if asset_type in synplant_seed_assets:
        return {
            "sample_id": "",
            "eligibility": "eligible",
            "confidence": 0.6,
            "rationale": [f"{asset_type} is a potential synplant seed candidate by heuristic rule"],
        }
    if asset_type in {"drum_break", "drum_loop", "percussion_loop"}:
        return {
            "sample_id": "",
            "eligibility": "ineligible",
            "confidence": 0.7,
            "rationale": [f"{asset_type} is routed as rhythm/groove source, not Synplant-first"],
        }
    return {
        "sample_id": "",
        "eligibility": "review_required",
        "confidence": 0.35,
        "rationale": ["heuristic classification uncertain"],
    }


def _texture_tags_from_path(relative_path: str, asset_type: AssetTypeName) -> list[str]:
    tags: list[str] = [asset_type]
    lower = relative_path.lower()
    for token in ["dark", "bright", "lofi", "organic", "noisy", "clean", "warm", "cold"]:
        if token in lower:
            tags.append(token)
    return sorted(set(tags))


def build_sample_seed_record(
    *,
    sample_id: str,
    library_id: str,
    source_path: Path,
    root_path: Path,
    extension: str,
    file_size_bytes: int,
    file_hash_sha256: str | None,
    duration_seconds: float | None,
    sample_rate: int | None,
    channels: int | None,
    fmt: str | None,
    authorization_status: str,
    review_status: str,
    intended_uses: list[str],
    limitations: list[str] | None = None,
) -> SampleSeedRecord:
    relative_path = source_path.resolve().relative_to(root_path.resolve()).as_posix()
    asset_type_guess, confidence, evidence, needs_review = classify_asset_type_guess(
        relative_path=relative_path,
        filename=source_path.name,
        duration_seconds=duration_seconds,
    )
    role_candidates = default_role_candidates_for_asset(asset_type_guess)
    return {
        "sample_id": sample_id,
        "library_id": library_id,
        "source_path": str(source_path.resolve()),
        "relative_path": relative_path,
        "filename": source_path.name,
        "extension": extension,
        "file_size_bytes": int(file_size_bytes),
        "file_hash_sha256": file_hash_sha256,
        "duration_seconds": duration_seconds,
        "sample_rate": sample_rate,
        "channels": channels,
        "format": fmt,
        "authorization_status": authorization_status,
        "review_status": review_status,
        "intended_uses": [str(item) for item in intended_uses],
        "role_candidates": role_candidates,
        "texture_tags": _texture_tags_from_path(relative_path, asset_type_guess),
        "feature_status": "not_started",
        "analysis_refs": [],
        "limitations": [str(item) for item in (limitations or [])],
        "asset_type_guess": asset_type_guess,
        "asset_type_confidence": confidence,
        "asset_type_evidence": evidence,
        "needs_human_review": needs_review,
        "source_type": "local_sample_seed_library",
        "ingestion_context": "sample_library_indexing",
        "asset_type_is_heuristic": True,
        "classification_method": "heuristic_filename_duration_v1",
    }


def build_sample_search_query(
    *,
    query_id: str,
    requested_roles: list[SampleRoleName],
    requested_asset_types: list[AssetTypeName],
    intended_use: str,
) -> SampleSearchQuery:
    return {
        "query_id": query_id,
        "requested_roles": requested_roles,
        "requested_asset_types": requested_asset_types,
        "intended_use": intended_use,
        "created_at": _now_iso(),
    }


def normalize_sample_id(library_id: str, relative_path: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", relative_path).strip("_")
    if not safe:
        safe = "sample"
    return f"{library_id}__{safe}"
