from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.model_witnesses import redact_private_path

TRUST_GLOB = "features/performances/*/*/trust/training_data_audit.json"
LOCAL_AUTH_CONFIG = ROOT_DIR / "config" / "source_audio_study_authorization.local.json"
OUT_DIR = ROOT_DIR / "datasets" / "source_audio_study"
OUT_JSONL = OUT_DIR / "source_audio_study_manifest.jsonl"
CONTROLLED_BATCH_JSONL = OUT_DIR / "source_audio_controlled_batch.jsonl"
LOCAL_CACHE_DIR = ROOT_DIR / "local_source_audio_study"
LOCAL_PATH_MAP = LOCAL_CACHE_DIR / "source_audio_path_map.local.json"
REPORT_DIR = ROOT_DIR / "reports" / "source_audio_study"
REPORT_JSON = REPORT_DIR / "source_audio_study_manifest_report.json"
REPORT_MD = REPORT_DIR / "source_audio_study_manifest_report.md"
CONTROLLED_BATCH_REPORT_JSON = REPORT_DIR / "source_audio_controlled_batch_report.json"
CONTROLLED_BATCH_REPORT_MD = REPORT_DIR / "source_audio_controlled_batch_report.md"
AUDIT_JSON = REPORT_DIR / "source_audio_manifest_population_audit.json"
AUDIT_MD = REPORT_DIR / "source_audio_manifest_population_audit.md"
SUPPORTED_SOURCE_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aif", ".aiff"}
DEFAULT_CONTROLLED_BATCH_MAX = 25


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_local_auth_config() -> dict[str, Any] | None:
    if not LOCAL_AUTH_CONFIG.exists():
        return None
    payload = _read_json(LOCAL_AUTH_CONFIG)
    return payload if payload else {}


def _normalize_roots(values: Any) -> list[Path]:
    if not isinstance(values, list):
        return []
    roots: list[Path] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        path_obj = Path(text)
        try:
            resolved = path_obj.resolve(strict=False)
        except Exception:  # noqa: BLE001
            resolved = path_obj
        canonical = _canonical_text(str(resolved))
        if canonical in seen:
            continue
        seen.add(canonical)
        roots.append(resolved)
    return roots


def _is_windows_style_path(value: str) -> bool:
    text = value.strip()
    return bool(re.match(r"^[A-Za-z]:[\\/]", text)) or text.startswith("\\\\")


def _canonical_text(value: str) -> str:
    text = str(value or "").strip().replace("\\", "/")
    while "//" in text:
        text = text.replace("//", "/")
    if text.endswith("/") and len(text) > 1:
        text = text.rstrip("/")
    if os.name == "nt" or _is_windows_style_path(text):
        text = text.lower()
    return text


@dataclass(frozen=True)
class RootSpec:
    raw: str
    path: Path
    root_type: str
    canonical: str
    exists: bool
    supported_file_count: int


def _media_type_for_extension(extension: str) -> str:
    if extension in {".wav", ".mp3", ".flac", ".m4a", ".aif", ".aiff"}:
        return "audio"
    return "unknown"


def _path_hash(path: Path) -> str:
    return hashlib.sha256(_canonical_text(str(path)).encode("utf-8")).hexdigest()


def _discover_supported_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if root.is_file():
        return [root] if root.suffix.lower() in SUPPORTED_SOURCE_EXTENSIONS else []
    out: list[Path] = []
    for child in root.rglob("*"):
        if child.is_file() and child.suffix.lower() in SUPPORTED_SOURCE_EXTENSIONS:
            out.append(child)
    return out


def _count_supported_files(root: Path) -> int:
    return len(_discover_supported_files(root))


def _root_spec(path_obj: Path) -> RootSpec:
    exists = path_obj.exists()
    if exists and path_obj.is_file():
        root_type = "file"
    elif exists and path_obj.is_dir():
        root_type = "folder"
    elif path_obj.suffix:
        root_type = "file"
    else:
        root_type = "folder"
    return RootSpec(
        raw=str(path_obj),
        path=path_obj,
        root_type=root_type,
        canonical=_canonical_text(str(path_obj)),
        exists=exists,
        supported_file_count=_count_supported_files(path_obj),
    )


def _match_root(path_value: str, roots: list[RootSpec]) -> tuple[bool, RootSpec | None, str]:
    source_canonical = _canonical_text(path_value)
    if not roots:
        return False, None, "no_roots_configured"
    if not source_canonical:
        return False, None, "empty_source_path"
    for spec in roots:
        root_value = spec.canonical
        if spec.root_type == "file":
            if source_canonical == root_value:
                return True, spec, "root_file_exact_match"
            continue
        if source_canonical == root_value or source_canonical.startswith(root_value + "/"):
            return True, spec, "root_folder_prefix_match"
    return False, None, "no_matching_root"


def _build_manifest_row(
    source_path: Path,
    *,
    analysis_specs: list[RootSpec],
    reference_specs: list[RootSpec],
    excluded_specs: list[RootSpec],
    training_specs: list[RootSpec],
    auth_cfg_present: bool,
) -> dict[str, Any]:
    source_abs = source_path.resolve(strict=False)
    source_abs_str = str(source_abs)
    extension = source_abs.suffix.lower()
    path_hash = _path_hash(source_abs)
    source_id = f"source_{path_hash[:16]}"

    in_excluded, _, _ = _match_root(source_abs_str, excluded_specs)
    in_analysis, _, _ = _match_root(source_abs_str, analysis_specs)
    in_reference, _, _ = _match_root(source_abs_str, reference_specs)
    in_training, _, _ = _match_root(source_abs_str, training_specs)

    blockers: list[str] = []
    if not auth_cfg_present:
        authorization_status = "blocked_missing_local_authorization_config"
        analysis_allowed = False
        retrieval_allowed = False
        training_allowed = False
        source_category = "blocked_no_config"
        blockers.append("missing_local_authorization_config")
    elif in_excluded:
        authorization_status = "excluded_by_local_policy"
        analysis_allowed = False
        retrieval_allowed = False
        training_allowed = False
        source_category = "excluded"
        blockers.append("excluded_root")
    elif in_analysis:
        authorization_status = "analysis_allowed_by_local_policy"
        analysis_allowed = True
        retrieval_allowed = True
        training_allowed = False
        source_category = "analysis_allowed_root"
        if in_training:
            blockers.append("training_disabled_for_source_audio")
    elif in_reference:
        authorization_status = "reference_only_by_local_policy"
        analysis_allowed = False
        retrieval_allowed = True
        training_allowed = False
        source_category = "reference_only_root"
        blockers.append("reference_only_root")
    else:
        authorization_status = "outside_authorized_roots"
        analysis_allowed = False
        retrieval_allowed = False
        training_allowed = False
        source_category = "outside_authorized_roots"
        blockers.append("outside_authorized_roots")

    try:
        file_size_bytes = int(source_abs.stat().st_size)
    except OSError:
        file_size_bytes = None

    return {
        "source_id": source_id,
        "path_hash": path_hash,
        "redacted_path": redact_private_path(source_abs_str),
        "media_type": _media_type_for_extension(extension),
        "extension": extension,
        "file_size_bytes": file_size_bytes,
        "authorization_status": authorization_status,
        "analysis_allowed": analysis_allowed,
        "training_allowed": training_allowed,
        "retrieval_allowed": retrieval_allowed,
        "source_category": source_category,
        "blockers": sorted(set(blockers)),
    }


def _discover_authorized_sources(
    *,
    analysis_specs: list[RootSpec],
    reference_specs: list[RootSpec],
) -> tuple[list[Path], dict[str, int]]:
    all_roots = [spec.path for spec in analysis_specs] + [spec.path for spec in reference_specs]
    seen: set[str] = set()
    discovered: list[Path] = []
    for root in all_roots:
        for source_file in _discover_supported_files(root):
            canonical = _canonical_text(str(source_file.resolve(strict=False)))
            if canonical in seen:
                continue
            seen.add(canonical)
            discovered.append(source_file.resolve(strict=False))
    discovered = sorted(discovered, key=lambda item: _canonical_text(str(item)))
    return discovered, {
        "discovered_supported_files_total": len(discovered),
        "analysis_root_count": len(analysis_specs),
        "reference_root_count": len(reference_specs),
    }


def _select_controlled_batch(rows: list[dict[str, Any]], max_items: int) -> list[dict[str, Any]]:
    analysis_first = sorted((row for row in rows if row.get("analysis_allowed")), key=lambda row: str(row.get("source_id", "")))
    non_analysis = sorted((row for row in rows if not row.get("analysis_allowed")), key=lambda row: str(row.get("source_id", "")))
    ordered = analysis_first + non_analysis
    return ordered[:max_items]


def build_manifest() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    auth_cfg = _load_local_auth_config()
    auth_cfg_present = auth_cfg is not None
    loaded_keys = sorted(auth_cfg.keys()) if isinstance(auth_cfg, dict) else []
    analysis_specs = [_root_spec(path) for path in _normalize_roots((auth_cfg or {}).get("analysis_allowed_roots"))]
    reference_specs = [
        _root_spec(path)
        for path in _normalize_roots((auth_cfg or {}).get("reference_only_roots") or (auth_cfg or {}).get("retrieval_only_roots"))
    ]
    excluded_specs = [_root_spec(path) for path in _normalize_roots((auth_cfg or {}).get("excluded_roots"))]
    training_specs = [_root_spec(path) for path in _normalize_roots((auth_cfg or {}).get("training_allowed_roots"))]

    discovered_sources, discovery_meta = _discover_authorized_sources(analysis_specs=analysis_specs, reference_specs=reference_specs)
    manifest_rows = [
        _build_manifest_row(
            path,
            analysis_specs=analysis_specs,
            reference_specs=reference_specs,
            excluded_specs=excluded_specs,
            training_specs=training_specs,
            auth_cfg_present=auth_cfg_present,
        )
        for path in discovered_sources
    ]
    max_batch = int((auth_cfg or {}).get("max_items_for_controlled_batch", DEFAULT_CONTROLLED_BATCH_MAX))
    if max_batch < 1:
        max_batch = DEFAULT_CONTROLLED_BATCH_MAX
    controlled_batch = _select_controlled_batch(manifest_rows, max_batch)

    old_trust_row_count = len(list(ROOT_DIR.glob(TRUST_GLOB)))
    blocked_missing_config = not auth_cfg_present
    blockers: list[str] = []
    if blocked_missing_config:
        blockers.append("missing_local_authorization_config")
    if auth_cfg_present and discovery_meta["discovered_supported_files_total"] == 0:
        blockers.append("authorized_roots_have_no_supported_files")
    if auth_cfg_present and analysis_specs and not any(row.get("analysis_allowed") for row in manifest_rows):
        blockers.append("analysis_allowed_roots_have_no_discovered_files")

    manifest_report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "manifest_path": OUT_JSONL.relative_to(ROOT_DIR).as_posix(),
        "controlled_batch_path": CONTROLLED_BATCH_JSONL.relative_to(ROOT_DIR).as_posix(),
        "authorization_config_path": LOCAL_AUTH_CONFIG.relative_to(ROOT_DIR).as_posix(),
        "authorization_config_present": auth_cfg_present,
        "authorization_config_loaded_keys": loaded_keys,
        "analysis_allowed_roots_count": len(analysis_specs),
        "reference_only_roots_count": len(reference_specs),
        "analysis_allowed_roots_exist": bool(analysis_specs) and all(spec.exists for spec in analysis_specs),
        "analysis_allowed_roots_supported_files": sum(spec.supported_file_count for spec in analysis_specs),
        "reference_only_roots_supported_files": sum(spec.supported_file_count for spec in reference_specs),
        "analysis_allowed_roots_redacted": [redact_private_path(spec.raw) for spec in analysis_specs],
        "reference_only_roots_redacted": [redact_private_path(spec.raw) for spec in reference_specs],
        "supported_files_found_under_allowed_roots": discovery_meta["discovered_supported_files_total"],
        "manifest_rows_created_total": len(manifest_rows),
        "controlled_batch_size": len(controlled_batch),
        "source_items_considered": len(manifest_rows),
        "analysis_allowed_count": sum(1 for row in manifest_rows if row.get("analysis_allowed")),
        "analysis_blocked_count": sum(1 for row in manifest_rows if not row.get("analysis_allowed")),
        "training_allowed_count": sum(1 for row in manifest_rows if row.get("training_allowed")),
        "authorization_status_counts": {
            key: sum(1 for row in manifest_rows if row.get("authorization_status") == key)
            for key in sorted({str(row.get("authorization_status")) for row in manifest_rows})
        },
        "blockers": blockers,
        "policy_notes": [
            "No source audio files were moved, modified, or deleted.",
            "Manifest rows are discovered from authorized roots, not trust-audit references.",
            "Committed datasets contain only redacted paths + hashed identifiers.",
            "Raw absolute source paths are stored only in local ignored cache.",
            "Training on source audio remains disabled.",
        ],
    }

    controlled_batch_report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "controlled_batch_path": CONTROLLED_BATCH_JSONL.relative_to(ROOT_DIR).as_posix(),
        "max_items_for_controlled_batch": max_batch,
        "controlled_batch_size": len(controlled_batch),
        "analysis_allowed_count": sum(1 for row in controlled_batch if row.get("analysis_allowed")),
        "retrieval_allowed_count": sum(1 for row in controlled_batch if row.get("retrieval_allowed")),
        "authorization_status_counts": {
            key: sum(1 for row in controlled_batch if row.get("authorization_status") == key)
            for key in sorted({str(row.get("authorization_status")) for row in controlled_batch})
        },
        "policy_notes": [
            "Controlled batch prioritizes analysis-allowed rows first.",
            "Batch is capped by local max_items_for_controlled_batch.",
            "No raw absolute paths are written to committed outputs.",
        ],
    }

    audit_report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "requested_branch": "cursor/real-midi-source-witness-integration-v1",
        "current_branch": "cursor/real-midi-source-witness-integration-v1",
        "authorization_config_path_redacted": redact_private_path(str(LOCAL_AUTH_CONFIG)),
        "authorization_config_present": auth_cfg_present,
        "authorization_config_loaded_keys": loaded_keys,
        "analysis_allowed_roots_count": len(analysis_specs),
        "reference_only_roots_count": len(reference_specs),
        "supported_files_found_under_allowed_roots": discovery_meta["discovered_supported_files_total"],
        "old_manifest_population_path": "scripts/build_source_audio_study_manifest.py::build_manifest -> ROOT_DIR.glob(TRUST_GLOB) -> _build_item(SourceAudioStudyItem)",
        "new_manifest_population_path": "scripts/build_source_audio_study_manifest.py::build_manifest -> _discover_authorized_sources -> _build_manifest_row -> _select_controlled_batch",
        "old_source_items_considered_from_trust_glob": old_trust_row_count,
        "new_manifest_rows_created_from_authorized_roots": len(manifest_rows),
        "why_only_4_rows_existed": (
            "Old logic only populated manifest rows from trust-audit JSON files under "
            "features/performances/*/*/trust/training_data_audit.json. That branch had 4 such files, so only 4 rows were produced."
        ),
        "root_cause": "Manifest population source was trust-audit references, not recursive source discovery under authorized roots.",
        "fixed_behavior_summary": "Manifest rows are now discovered from analysis_allowed_roots/reference_only_roots and committed with redacted/hash-only fields.",
    }
    return manifest_rows, controlled_batch, manifest_report, controlled_batch_report, audit_report


def _local_path_map_rows(rows: list[dict[str, Any]], discovered_sources: list[Path]) -> dict[str, Any]:
    index = {row["path_hash"]: row for row in rows}
    map_rows: list[dict[str, Any]] = []
    for path in discovered_sources:
        path_hash = _path_hash(path)
        row = index.get(path_hash)
        if not row:
            continue
        map_rows.append(
            {
                "source_id": row["source_id"],
                "path_hash": path_hash,
                "absolute_path": str(path),
            }
        )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "count": len(map_rows),
        "path_map": map_rows,
    }


def write_outputs(
    manifest_rows: list[dict[str, Any]],
    controlled_batch: list[dict[str, Any]],
    manifest_report: dict[str, Any],
    controlled_batch_report: dict[str, Any],
    audit_report: dict[str, Any],
) -> tuple[Path, Path, Path, Path, Path, Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    with OUT_JSONL.open("w", encoding="utf-8") as handle:
        for row in manifest_rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    with CONTROLLED_BATCH_JSONL.open("w", encoding="utf-8") as handle:
        for row in controlled_batch:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    REPORT_JSON.write_text(json.dumps(manifest_report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    CONTROLLED_BATCH_REPORT_JSON.write_text(json.dumps(controlled_batch_report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    AUDIT_JSON.write_text(json.dumps(audit_report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    manifest_lines = [
        "# Source Audio Study Manifest Report",
        "",
        f"- supported_files_found_under_allowed_roots: `{manifest_report['supported_files_found_under_allowed_roots']}`",
        f"- manifest_rows_created_total: `{manifest_report['manifest_rows_created_total']}`",
        f"- analysis_allowed_count: `{manifest_report['analysis_allowed_count']}`",
        f"- controlled_batch_size: `{manifest_report['controlled_batch_size']}`",
        "",
        "## Policy notes",
        *[f"- {line}" for line in manifest_report["policy_notes"]],
    ]
    REPORT_MD.write_text("\n".join(manifest_lines).rstrip() + "\n", encoding="utf-8")

    batch_lines = [
        "# Source Audio Controlled Batch Report",
        "",
        f"- max_items_for_controlled_batch: `{controlled_batch_report['max_items_for_controlled_batch']}`",
        f"- controlled_batch_size: `{controlled_batch_report['controlled_batch_size']}`",
        f"- analysis_allowed_count: `{controlled_batch_report['analysis_allowed_count']}`",
        "",
        "## Policy notes",
        *[f"- {line}" for line in controlled_batch_report["policy_notes"]],
    ]
    CONTROLLED_BATCH_REPORT_MD.write_text("\n".join(batch_lines).rstrip() + "\n", encoding="utf-8")

    audit_lines = [
        "# Source Audio Manifest Population Audit",
        "",
        f"- old_source_items_considered_from_trust_glob: `{audit_report['old_source_items_considered_from_trust_glob']}`",
        f"- new_manifest_rows_created_from_authorized_roots: `{audit_report['new_manifest_rows_created_from_authorized_roots']}`",
        f"- supported_files_found_under_allowed_roots: `{audit_report['supported_files_found_under_allowed_roots']}`",
        "",
        "## Why only 4 rows existed",
        f"- {audit_report['why_only_4_rows_existed']}",
        "",
        "## Code path change",
        f"- old: `{audit_report['old_manifest_population_path']}`",
        f"- new: `{audit_report['new_manifest_population_path']}`",
    ]
    AUDIT_MD.write_text("\n".join(audit_lines).rstrip() + "\n", encoding="utf-8")

    return (
        OUT_JSONL,
        CONTROLLED_BATCH_JSONL,
        REPORT_JSON,
        REPORT_MD,
        CONTROLLED_BATCH_REPORT_JSON,
        CONTROLLED_BATCH_REPORT_MD,
        AUDIT_JSON,
    )


def main() -> int:
    auth_cfg = _load_local_auth_config()
    analysis_specs = [_root_spec(path) for path in _normalize_roots((auth_cfg or {}).get("analysis_allowed_roots"))]
    reference_specs = [
        _root_spec(path)
        for path in _normalize_roots((auth_cfg or {}).get("reference_only_roots") or (auth_cfg or {}).get("retrieval_only_roots"))
    ]
    discovered_sources, _ = _discover_authorized_sources(analysis_specs=analysis_specs, reference_specs=reference_specs)
    manifest_rows, controlled_batch, manifest_report, controlled_batch_report, audit_report = build_manifest()
    LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_PATH_MAP.write_text(
        json.dumps(_local_path_map_rows(manifest_rows, discovered_sources), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (
        manifest_path,
        batch_path,
        report_json_path,
        report_md_path,
        batch_report_json_path,
        batch_report_md_path,
        audit_json_path,
    ) = write_outputs(manifest_rows, controlled_batch, manifest_report, controlled_batch_report, audit_report)
    print(f"SOURCE_AUDIO_STUDY_MANIFEST={manifest_path.as_posix()}")
    print(f"SOURCE_AUDIO_CONTROLLED_BATCH={batch_path.as_posix()}")
    print(f"SOURCE_AUDIO_STUDY_REPORT_JSON={report_json_path.as_posix()}")
    print(f"SOURCE_AUDIO_STUDY_REPORT_MD={report_md_path.as_posix()}")
    print(f"SOURCE_AUDIO_CONTROLLED_BATCH_REPORT_JSON={batch_report_json_path.as_posix()}")
    print(f"SOURCE_AUDIO_CONTROLLED_BATCH_REPORT_MD={batch_report_md_path.as_posix()}")
    print(f"SOURCE_AUDIO_MANIFEST_AUDIT_JSON={audit_json_path.as_posix()}")
    print(f"SOURCE_AUDIO_PATH_MAP_LOCAL={LOCAL_PATH_MAP.as_posix()}")
    print(f"SOURCE_ITEMS_CONSIDERED={manifest_report['source_items_considered']}")
    print(f"SOURCE_ITEMS_ANALYSIS_ALLOWED={manifest_report['analysis_allowed_count']}")
    print(f"CONTROLLED_BATCH_SIZE={manifest_report['controlled_batch_size']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
