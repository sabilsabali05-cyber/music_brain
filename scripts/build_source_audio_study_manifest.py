from __future__ import annotations

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
from features.source_audio_study import SourceAudioStudyItem

TRUST_GLOB = "features/performances/*/*/trust/training_data_audit.json"
LOCAL_AUTH_CONFIG = ROOT_DIR / "config" / "source_audio_study_authorization.local.json"
OUT_DIR = ROOT_DIR / "datasets" / "source_audio_study"
OUT_JSONL = OUT_DIR / "source_audio_study_manifest.jsonl"
REPORT_DIR = ROOT_DIR / "reports" / "source_audio_study"
REPORT_JSON = REPORT_DIR / "source_audio_study_manifest_report.json"
REPORT_MD = REPORT_DIR / "source_audio_study_manifest_report.md"
SUPPORTED_SOURCE_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aif", ".aiff"}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


def _load_local_auth_config() -> dict[str, Any] | None:
    if not LOCAL_AUTH_CONFIG.exists():
        return None
    payload = _read_json(LOCAL_AUTH_CONFIG)
    return payload if payload else {}


def _normalize_roots(values: Any) -> list[Path]:
    if not isinstance(values, list):
        return []
    roots: list[Path] = []
    for value in values:
        text = str(value).strip()
        if text:
            roots.append(Path(text))
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


def _path_candidates(path_value: str, *, root_dir: Path = ROOT_DIR) -> set[str]:
    text = str(path_value or "").strip()
    if not text:
        return set()
    candidates: set[str] = {_canonical_text(text)}
    path_obj = Path(text)
    try:
        resolved = path_obj.resolve(strict=False)
        candidates.add(_canonical_text(str(resolved)))
    except Exception:  # noqa: BLE001
        pass
    if not path_obj.is_absolute():
        try:
            resolved_local = (root_dir / path_obj).resolve(strict=False)
            candidates.add(_canonical_text(str(resolved_local)))
        except Exception:  # noqa: BLE001
            pass
    return {item for item in candidates if item}


@dataclass(frozen=True)
class RootSpec:
    raw: str
    root_type: str
    candidates: tuple[str, ...]
    exists: bool
    supported_file_count: int


def _count_supported_files(root_path: Path) -> int:
    if not root_path.exists():
        return 0
    if root_path.is_file():
        return 1 if root_path.suffix.lower() in SUPPORTED_SOURCE_EXTENSIONS else 0
    count = 0
    for child in root_path.rglob("*"):
        if child.is_file() and child.suffix.lower() in SUPPORTED_SOURCE_EXTENSIONS:
            count += 1
    return count


def _root_spec(path_obj: Path) -> RootSpec:
    raw = str(path_obj)
    exists = path_obj.exists()
    root_type = "unknown"
    if exists and path_obj.is_file():
        root_type = "file"
    elif exists and path_obj.is_dir():
        root_type = "folder"
    elif path_obj.suffix:
        root_type = "file"
    else:
        root_type = "folder"
    candidates = tuple(sorted(_path_candidates(raw)))
    return RootSpec(
        raw=raw,
        root_type=root_type,
        candidates=candidates,
        exists=exists,
        supported_file_count=_count_supported_files(path_obj),
    )


def _match_root(path_value: str, roots: list[RootSpec]) -> tuple[bool, RootSpec | None, str]:
    source_candidates = _path_candidates(path_value)
    if not roots:
        return False, None, "no_analysis_allowed_roots_configured"
    if not source_candidates:
        return False, None, "empty_source_path"

    for spec in roots:
        for source_value in source_candidates:
            for root_value in spec.candidates:
                if spec.root_type == "file":
                    if source_value == root_value:
                        return True, spec, "root_file_exact_match"
                    continue
                if source_value == root_value or source_value.startswith(root_value + "/"):
                    return True, spec, "root_folder_prefix_match"
    return False, None, "no_matching_analysis_allowed_root"


def _build_item(path: Path, payload: dict[str, Any], root_specs: list[RootSpec], auth_cfg: dict[str, Any] | None = None) -> SourceAudioStudyItem:
    artifacts = payload.get("artifacts", {}) if isinstance(payload.get("artifacts"), dict) else {}
    source_ref = str(artifacts.get("source_audio_reference", "<PRIVATE_LOCAL_PATH>/unknown"))
    source_ref_norm = _canonical_text(source_ref)
    perf_id = str(payload.get("performance_id", path.parents[2].name))
    trust_auth = str(payload.get("authorization_status", "unknown")).strip().lower() or "unknown"
    retrieval_allowed = _bool(payload.get("retrieval_allowed"), default=True)
    training_allowed = False
    analysis_allowed = False
    auth = "blocked_missing_local_authorization_config"
    policy_notes: list[str] = []
    if auth_cfg is None:
        retrieval_allowed = True
        analysis_allowed = False
        training_allowed = False
        policy_notes.append("analysis blocked: missing local authorization config")
    else:
        excluded_specs = [_root_spec(root) for root in _normalize_roots(auth_cfg.get("excluded_roots"))]
        retrieval_specs = [_root_spec(root) for root in _normalize_roots(auth_cfg.get("retrieval_only_roots") or auth_cfg.get("reference_only_roots"))]
        training_specs = [_root_spec(root) for root in _normalize_roots(auth_cfg.get("training_allowed_roots"))]
        in_excluded, excluded_root, _ = _match_root(source_ref, excluded_specs)
        in_retrieval_only, retrieval_root, _ = _match_root(source_ref, retrieval_specs)
        in_analysis, analysis_root, analysis_reason = _match_root(source_ref, root_specs)
        in_training, training_root, _ = _match_root(source_ref, training_specs)
        if in_excluded:
            auth = "excluded_by_local_policy"
            retrieval_allowed = False
            policy_notes.append(f"matched excluded root: {excluded_root.raw if excluded_root else 'unknown'}")
        elif in_retrieval_only:
            auth = "retrieval_only_by_local_policy"
            retrieval_allowed = True
            policy_notes.append(f"matched retrieval-only root: {retrieval_root.raw if retrieval_root else 'unknown'}")
        elif in_analysis:
            analysis_allowed = _bool(payload.get("analysis_allowed"), default=True)
            retrieval_allowed = True
            auth = trust_auth if trust_auth != "unknown" else "analysis_allowed_by_local_policy"
            policy_notes.append(f"matched analysis root: {analysis_root.raw if analysis_root else 'unknown'} ({analysis_reason})")
        else:
            auth = "not_in_analysis_allowed_roots"
            retrieval_allowed = True
            policy_notes.append(analysis_reason)
        # Training always remains opt-in and requires explicit local root + row opt-in.
        training_allowed = bool(in_training and _bool(payload.get("training_allowed"), default=False))
        if training_allowed:
            policy_notes.append(f"training explicitly authorized by local config + row: {training_root.raw if training_root else 'unknown'}")
        else:
            policy_notes.append("training disabled unless explicitly authorized")
    try:
        trust_rel = path.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        trust_rel = path.as_posix()
    return SourceAudioStudyItem(
        item_id=f"source_audio_{perf_id}",
        source_audio_ref=source_ref,
        source_audio_ref_redacted=source_ref,
        authorization_status=auth,
        retrieval_allowed=retrieval_allowed,
        training_allowed=training_allowed,
        analysis_allowed=analysis_allowed,
        policy_separation={
            "authorization_scope": auth,
            "analysis_allowed": analysis_allowed,
            "training_allowed": training_allowed,
            "retrieval_allowed": retrieval_allowed,
            "must_not_train_on_audio": not training_allowed,
            "must_not_analyze_raw_audio_without_permission": not analysis_allowed,
            "policy_notes": policy_notes,
                "normalized_source_path": source_ref_norm,
        },
        provenance={
            "trust_audit_path": trust_rel,
            "generated_at": datetime.now(UTC).isoformat(),
        },
    )


def build_manifest() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    items: list[dict[str, Any]] = []
    auth_cfg = _load_local_auth_config()
    loaded_keys = sorted(auth_cfg.keys()) if isinstance(auth_cfg, dict) else []
    analysis_roots = _normalize_roots((auth_cfg or {}).get("analysis_allowed_roots"))
    root_specs = [_root_spec(path) for path in analysis_roots]
    for path in sorted(ROOT_DIR.glob(TRUST_GLOB)):
        payload = _read_json(path)
        if not payload:
            continue
        item = _build_item(path, payload, root_specs, auth_cfg)
        items.append(item.to_dict())

    matched_items = sum(1 for row in items if row.get("authorization_status") not in {"not_in_analysis_allowed_roots", "excluded_by_local_policy", "retrieval_only_by_local_policy", "blocked_missing_local_authorization_config"})
    analysis_allowed_count = sum(1 for row in items if row.get("analysis_allowed"))
    roots_exist = bool(root_specs) and all(spec.exists for spec in root_specs)
    supported_files_under_roots = sum(spec.supported_file_count for spec in root_specs)
    blockers: list[str] = []
    if auth_cfg is None:
        blockers.append("missing_local_authorization_config")
    if auth_cfg is not None and root_specs and matched_items == 0:
        blockers.append("authorization_roots_match_no_items")
    if roots_exist and supported_files_under_roots == 0:
        blockers.append("allowed_roots_exist_but_no_supported_files")
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "manifest_path": OUT_JSONL.relative_to(ROOT_DIR).as_posix(),
        "authorization_config_path": LOCAL_AUTH_CONFIG.relative_to(ROOT_DIR).as_posix(),
        "authorization_config_present": auth_cfg is not None,
        "authorization_config_loaded_keys": loaded_keys,
        "analysis_allowed_roots_count": len(root_specs),
        "analysis_allowed_roots_exist": roots_exist,
        "analysis_allowed_roots_supported_files": supported_files_under_roots,
        "analysis_allowed_roots_redacted": [redact_private_path(spec.raw) for spec in root_specs],
        "analysis_allowed_root_details": [
            {
                "root_redacted": redact_private_path(spec.raw),
                "root_type": spec.root_type,
                "exists": spec.exists,
                "supported_file_count": spec.supported_file_count,
            }
            for spec in root_specs
        ],
        "source_items_matched_to_allowed_roots": matched_items,
        "source_items_considered": len(items),
        "analysis_allowed_count": analysis_allowed_count,
        "analysis_blocked_count": sum(1 for row in items if not row.get("analysis_allowed")),
        "training_allowed_count": sum(1 for row in items if row.get("training_allowed")),
        "blockers": blockers,
        "authorization_status_counts": {
            key: sum(1 for row in items if row.get("authorization_status") == key) for key in sorted({str(row.get("authorization_status")) for row in items})
        },
        "policy_notes": [
            "No source audio files were moved, modified, or deleted.",
            "Manifest rows separate retrieval/training/analysis authorization decisions.",
            "Raw audio analysis is blocked unless analysis_allowed=true per row.",
            "Missing local authorization config blocks all analysis via missing_local_authorization_config.",
            "Excluded and retrieval-only roots are never analyzed.",
            "Training is disabled unless explicitly allowed.",
            "Source-to-root authorization matching uses normalized absolute candidates and prefix matching.",
        ],
    }
    return items, report


def write_outputs(items: list[dict[str, Any]], report: dict[str, Any]) -> tuple[Path, Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("w", encoding="utf-8") as handle:
        for row in items:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Source Audio Study Manifest Report",
        "",
        f"- source_items_considered: `{report['source_items_considered']}`",
        f"- analysis_allowed_count: `{report['analysis_allowed_count']}`",
        f"- analysis_blocked_count: `{report['analysis_blocked_count']}`",
        f"- training_allowed_count: `{report['training_allowed_count']}`",
        "",
        "## Policy notes",
        *[f"- {line}" for line in report["policy_notes"]],
    ]
    REPORT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return OUT_JSONL, REPORT_JSON, REPORT_MD


def main() -> int:
    items, report = build_manifest()
    manifest_path, json_path, md_path = write_outputs(items, report)
    print(f"SOURCE_AUDIO_STUDY_MANIFEST={manifest_path.as_posix()}")
    print(f"SOURCE_AUDIO_STUDY_REPORT_JSON={json_path.as_posix()}")
    print(f"SOURCE_AUDIO_STUDY_REPORT_MD={md_path.as_posix()}")
    print(f"SOURCE_ITEMS_CONSIDERED={report['source_items_considered']}")
    print(f"SOURCE_ITEMS_ANALYSIS_ALLOWED={report['analysis_allowed_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
