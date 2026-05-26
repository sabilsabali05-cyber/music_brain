from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.source_sample_pack import SamplePackCandidate

CONFIG_PATH = ROOT_DIR / "config" / "source_audio_sample_pack.local.json"
CONTROLLED_BATCH_PATH = ROOT_DIR / "datasets" / "source_audio_study" / "source_audio_controlled_batch.jsonl"
MANIFEST_PATH = ROOT_DIR / "datasets" / "source_audio_study" / "source_audio_study_manifest.jsonl"
CONSENSUS_PATH = ROOT_DIR / "datasets" / "model_witnesses" / "source_audio_witness_consensus.jsonl"
DOSSIER_PATH = ROOT_DIR / "reports" / "source_taste_understanding" / "source_database_taste_dossier.json"
LOCAL_PATH_MAP = ROOT_DIR / "local_source_audio_study" / "source_audio_path_map.local.json"

OUT_DIR = ROOT_DIR / "datasets" / "source_sample_pack"
OUT_JSONL = OUT_DIR / "source_loop_candidates.jsonl"
REPORT_DIR = ROOT_DIR / "reports" / "source_sample_pack"
REPORT_JSON = REPORT_DIR / "source_loop_candidate_report.json"
REPORT_MD = REPORT_DIR / "source_loop_candidate_report.md"

PRIVATE_MARKERS = ("C:/Users/", "C:\\Users\\", "/Users/")
ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "drums": ("drum", "kick", "snare", "hat", "perc", "break"),
    "bass": ("bass", "sub"),
    "melody": ("mel", "synth", "lead", "keys", "piano", "chord"),
    "vocals": ("vocal", "vox", "voice", "acapella"),
    "texture": ("pad", "fx", "texture", "atmo", "noise", "amb"),
}


@dataclass(frozen=True)
class DiscoveryConfig:
    analysis_allowed_roots: list[Path]
    export_allowed_roots: list[Path]
    sample_pack_allowed_roots: list[Path]
    reference_only_roots: list[Path]
    max_sample_pack_source_items: int
    max_loops_per_source: int
    allowed_loop_lengths_bars: list[int]
    allow_audio_loop_export: bool
    allow_reference_to_midi_starters: bool


def _canonical_path_text(value: str) -> str:
    text = str(value or "").strip().replace("\\", "/")
    while "//" in text:
        text = text.replace("//", "/")
    if text.endswith("/") and len(text) > 1:
        text = text.rstrip("/")
    if re.match(r"^[A-Za-z]:/", text):
        text = text.lower()
    return text


def _normalize_roots(values: Any) -> list[Path]:
    if not isinstance(values, list):
        return []
    out: list[Path] = []
    seen: set[str] = set()
    for value in values:
        raw = str(value or "").strip()
        if not raw:
            continue
        path = Path(raw).resolve(strict=False)
        canonical = _canonical_path_text(str(path))
        if canonical in seen:
            continue
        seen.add(canonical)
        out.append(path)
    return out


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _load_config() -> DiscoveryConfig:
    payload = _read_json(CONFIG_PATH)
    allowed_bars = [int(item) for item in payload.get("allowed_loop_lengths_bars", [2, 4, 8]) if int(item) > 0]
    if not allowed_bars:
        allowed_bars = [2, 4, 8]
    max_sources = int(payload.get("max_sample_pack_source_items", 25))
    max_loops_per_source = int(payload.get("max_loops_per_source", 2))
    return DiscoveryConfig(
        analysis_allowed_roots=_normalize_roots(payload.get("analysis_allowed_roots", [])),
        export_allowed_roots=_normalize_roots(payload.get("export_allowed_roots", [])),
        sample_pack_allowed_roots=_normalize_roots(payload.get("sample_pack_allowed_roots", [])),
        reference_only_roots=_normalize_roots(payload.get("reference_only_roots", [])),
        max_sample_pack_source_items=max(max_sources, 1),
        max_loops_per_source=max(max_loops_per_source, 1),
        allowed_loop_lengths_bars=sorted(set(allowed_bars)),
        allow_audio_loop_export=bool(payload.get("allow_audio_loop_export", False)),
        allow_reference_to_midi_starters=bool(payload.get("allow_reference_to_midi_starters", False)),
    )


def _load_path_map() -> dict[str, str]:
    payload = _read_json(LOCAL_PATH_MAP)
    rows = payload.get("path_map")
    if not isinstance(rows, list):
        return {}
    out: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        path_hash = str(row.get("path_hash", "")).strip()
        absolute_path = str(row.get("absolute_path", "")).strip()
        if path_hash and absolute_path:
            out[path_hash] = absolute_path
    return out


def _path_in_roots(path_text: str, roots: list[Path]) -> bool:
    canonical = _canonical_path_text(path_text)
    for root in roots:
        root_canonical = _canonical_path_text(str(root))
        if canonical == root_canonical or canonical.startswith(root_canonical + "/"):
            return True
    return False


def _infer_role(redacted_path: str) -> tuple[str, float]:
    lower = redacted_path.lower()
    for role, keywords in ROLE_KEYWORDS.items():
        if any(keyword in lower for keyword in keywords):
            return role, 0.7
    return "unknown", 0.2


def _infer_bpm(redacted_path: str) -> tuple[float | None, str]:
    match = re.search(r"(^|[_\-\s])([6-9][0-9]|1[0-9]{2}|2[0-2][0-9])(?=([_\-\s]|$))", redacted_path)
    if not match:
        return None, "none"
    return float(match.group(2)), "filename_hint"


def _infer_key(redacted_path: str) -> tuple[str | None, str]:
    match = re.search(r"([A-Ga-g](?:#|b)?(?:maj|min|m)?)", redacted_path)
    if not match:
        return None, "none"
    return match.group(1).upper(), "filename_hint"


def _consensus_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id = str(row.get("item_id", "")).strip()
        if item_id:
            out[item_id] = row
    return out


def _safe_duration_seconds(bar_length: int, bpm: float | None) -> float | None:
    if bpm is None or bpm <= 0:
        return None
    beats = float(bar_length * 4)
    return round((beats * 60.0) / bpm, 3)


def _candidate_id(source_id: str, role: str, bar_length: int, loop_index: int) -> str:
    digest = hashlib.sha256(f"{source_id}:{role}:{bar_length}:{loop_index}".encode("utf-8")).hexdigest()[:12]
    return f"candidate_{digest}"


def build_candidates() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    config = _load_config()
    controlled_batch = _read_jsonl(CONTROLLED_BATCH_PATH)
    manifest_rows = _read_jsonl(MANIFEST_PATH)
    manifest_index = {str(row.get("source_id", "")).strip(): row for row in manifest_rows if row.get("source_id")}
    path_map = _load_path_map()
    consensus = _consensus_index(_read_jsonl(CONSENSUS_PATH))
    dossier = _read_json(DOSSIER_PATH)

    selected_sources = controlled_batch[: config.max_sample_pack_source_items]
    candidates: list[SamplePackCandidate] = []
    skipped_reference_only_audio = 0
    blocked_export_by_policy = 0
    missing_path_map = 0

    for row in selected_sources:
        source_id = str(row.get("source_id", "")).strip()
        if not source_id:
            continue
        source_manifest = manifest_index.get(source_id, row)
        path_hash = str(source_manifest.get("path_hash", "")).strip()
        redacted_path = str(source_manifest.get("redacted_path", "<PRIVATE_LOCAL_PATH>/unknown"))
        absolute_path = path_map.get(path_hash, "")
        if not absolute_path:
            missing_path_map += 1
        role, role_confidence = _infer_role(redacted_path)
        bpm_estimate, bpm_source = _infer_bpm(redacted_path)
        key_estimate, key_source = _infer_key(redacted_path)

        in_reference_only = bool(absolute_path) and _path_in_roots(absolute_path, config.reference_only_roots)
        in_sample_pack_root = bool(absolute_path) and _path_in_roots(absolute_path, config.sample_pack_allowed_roots)
        in_export_root = bool(absolute_path) and _path_in_roots(absolute_path, config.export_allowed_roots)
        analysis_allowed = bool(source_manifest.get("analysis_allowed", False))
        can_export_audio = (
            config.allow_audio_loop_export
            and analysis_allowed
            and in_sample_pack_root
            and in_export_root
            and not in_reference_only
        )

        if in_reference_only:
            skipped_reference_only_audio += 1
        if not can_export_audio:
            blocked_export_by_policy += 1

        witness_row = consensus.get(source_id, {})
        witness_ids = [str(item) for item in witness_row.get("agreeing_witnesses", []) if str(item).strip()]
        witness_confidence = witness_row.get("confidence")
        if witness_confidence is not None:
            try:
                witness_confidence = float(witness_confidence)
            except (TypeError, ValueError):
                witness_confidence = None

        loop_count = min(config.max_loops_per_source, len(config.allowed_loop_lengths_bars))
        for loop_index in range(loop_count):
            bar_length = config.allowed_loop_lengths_bars[loop_index]
            duration = _safe_duration_seconds(bar_length, bpm_estimate)
            blockers: list[str] = []
            if not analysis_allowed:
                blockers.append("analysis_not_allowed")
            if not in_sample_pack_root:
                blockers.append("outside_sample_pack_allowed_roots")
            if in_reference_only:
                blockers.append("reference_only_source")
            if can_export_audio and duration is None:
                blockers.append("missing_bpm_for_audio_export")
            if not absolute_path:
                blockers.append("missing_local_path_map")

            candidate = SamplePackCandidate(
                candidate_id=_candidate_id(source_id, role, bar_length, loop_index),
                source_id=source_id,
                path_hash=path_hash,
                source_redacted_path=redacted_path,
                role=role,
                role_confidence=role_confidence,
                bar_length=bar_length,
                bpm_estimate=bpm_estimate,
                bpm_estimate_source=bpm_source,
                key_estimate=key_estimate,
                key_estimate_source=key_source,
                start_seconds=float(loop_index) * 0.5,
                duration_seconds=duration,
                analysis_allowed=analysis_allowed,
                export_allowed=can_export_audio,
                reference_only=in_reference_only,
                from_controlled_batch=True,
                witness_ids=witness_ids,
                witness_consensus_confidence=witness_confidence,
                evidence_summary="Derived from controlled batch + witness consensus + local policy roots.",
                policy_blockers=sorted(set(blockers)),
            )
            candidates.append(candidate)

    candidate_rows = [row.to_dict() for row in candidates]
    role_counts: dict[str, int] = {}
    for row in candidate_rows:
        role = str(row.get("role", "unknown"))
        role_counts[role] = role_counts.get(role, 0) + 1

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_items_considered": len(selected_sources),
        "loop_candidates_found": len(candidate_rows),
        "roles": role_counts,
        "reference_only_sources_seen": skipped_reference_only_audio,
        "blocked_for_audio_export_by_policy": blocked_export_by_policy,
        "allow_audio_loop_export": config.allow_audio_loop_export,
        "allow_reference_to_midi_starters": config.allow_reference_to_midi_starters,
        "allowed_loop_lengths_bars": config.allowed_loop_lengths_bars,
        "max_sample_pack_source_items": config.max_sample_pack_source_items,
        "max_loops_per_source": config.max_loops_per_source,
        "missing_local_path_map_sources": missing_path_map,
        "witness_records_available": len(consensus),
        "taste_dossier_present": bool(dossier),
        "policy_checks": {
            "no_training_performed": True,
            "no_cloud_calls_performed": True,
            "no_audio_export_in_discovery": True,
        },
        "private_paths_detected": any(
            marker in json.dumps({"candidates": candidate_rows, "report": role_counts})
            for marker in PRIVATE_MARKERS
        ),
        "limitations": [
            "Tempo and key are heuristic filename hints only when present.",
            "No model availability is fabricated; witness data is pass-through only.",
            "Audio is never exported in discovery.",
        ],
    }
    return candidate_rows, report


def write_outputs(candidate_rows: list[dict[str, Any]], report: dict[str, Any]) -> tuple[Path, Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with OUT_JSONL.open("w", encoding="utf-8") as handle:
        for row in candidate_rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Source Loop Candidate Discovery Report",
        "",
        f"- source_items_considered: `{report['source_items_considered']}`",
        f"- loop_candidates_found: `{report['loop_candidates_found']}`",
        f"- reference_only_sources_seen: `{report['reference_only_sources_seen']}`",
        f"- blocked_for_audio_export_by_policy: `{report['blocked_for_audio_export_by_policy']}`",
        f"- private_paths_detected: `{report['private_paths_detected']}`",
        "",
        "## Roles",
    ]
    if report["roles"]:
        for role, count in sorted(report["roles"].items()):
            lines.append(f"- `{role}`: `{count}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Policy checks"])
    for key, value in report["policy_checks"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Limitations"])
    lines.extend([f"- {line}" for line in report["limitations"]])
    REPORT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return OUT_JSONL, REPORT_MD, REPORT_JSON


def main() -> int:
    candidate_rows, report = build_candidates()
    jsonl_path, md_path, json_path = write_outputs(candidate_rows, report)
    print(f"SOURCE_LOOP_CANDIDATES_JSONL={jsonl_path.as_posix()}")
    print(f"SOURCE_LOOP_CANDIDATE_REPORT_MD={md_path.as_posix()}")
    print(f"SOURCE_LOOP_CANDIDATE_REPORT_JSON={json_path.as_posix()}")
    print(f"SOURCE_ITEMS_CONSIDERED={report['source_items_considered']}")
    print(f"LOOP_CANDIDATES_FOUND={report['loop_candidates_found']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
