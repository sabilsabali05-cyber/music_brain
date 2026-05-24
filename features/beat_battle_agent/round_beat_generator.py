from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agent_config_schema import BeatBattleAgentConfig
from .agent_state_schema import load_or_default_state, save_state


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_latest_manual_manifest(project_root: Path) -> tuple[dict[str, Any] | None, str]:
    pointer = project_root / "datasets" / "beat_battle_agent" / "manual_rounds" / "latest_round_manifest.txt"
    if not pointer.exists():
        return None, "missing_manual_round_manifest"
    manifest_path = Path(pointer.read_text(encoding="utf-8").strip())
    if not manifest_path.is_absolute():
        manifest_path = (project_root / manifest_path).resolve()
    if not manifest_path.exists():
        return None, "missing_manual_round_manifest"
    manifest = _load_json(manifest_path)
    if not manifest:
        return None, "invalid_manual_round_manifest"
    return manifest, ""


def _build_submission_drafts(round_id: str, sound_ids: list[str], drafts_target: int) -> list[dict[str, Any]]:
    drafts: list[dict[str, Any]] = []
    for idx in range(drafts_target):
        draft_id = f"{round_id}_submission_{idx + 1:02d}"
        drafts.append(
            {
                "draft_id": draft_id,
                "round_id": round_id,
                "draft_type": "submission",
                "sound_ids": sound_ids[: min(12, len(sound_ids))],
                "uses_only_provided_round_sounds": True,
                "synplant_variations_used": False,
                "submission_safe": True,
                "ranker_input_score": round(0.55 + (idx % 9) * 0.035, 4),
            }
        )
    return drafts


def _build_optional_study_drafts(round_id: str, selected_count: int) -> list[dict[str, Any]]:
    if selected_count <= 0:
        return []
    rows: list[dict[str, Any]] = []
    for idx in range(min(4, selected_count)):
        rows.append(
            {
                "draft_id": f"{round_id}_study_remix_{idx + 1:02d}",
                "round_id": round_id,
                "draft_type": "study_remix",
                "uses_only_provided_round_sounds": False,
                "synplant_variations_used": True,
                "submission_safe": False,
                "study_allowed": True,
                "submission_allowed": False,
                "ranker_input_score": round(0.4 + idx * 0.02, 4),
            }
        )
    return rows


def generate_round_beats(project_root: Path, config: BeatBattleAgentConfig, round_id: str) -> dict[str, Any]:
    manifest, blocker = _load_latest_manual_manifest(project_root)
    if manifest is None:
        return {"round_id": round_id, "drafts_generated": 0, "output_root": "", "submission_allowed": False, "legal_sound_usage_only": True, "blocker": blocker}
    sound_rows = manifest.get("sounds", [])
    sound_rows = sound_rows if isinstance(sound_rows, list) else []
    sound_ids = [str(row.get("sound_id", "")).strip() for row in sound_rows if isinstance(row, dict) and str(row.get("sound_id", "")).strip()]
    if not sound_ids:
        return {"round_id": round_id, "drafts_generated": 0, "output_root": "", "submission_allowed": False, "legal_sound_usage_only": True, "blocker": "missing_sound_ids"}

    selected_variations = _load_json(project_root / "reports" / "beat_battle_agent" / f"{round_id}_selected_synplant_variations.json")
    selected_count = int(selected_variations.get("selected_count", 0))
    drafts_target = max(config.min_drafts_per_round, 8)
    round_root = project_root / config.paths.round_outputs_root / round_id
    drafts_root = round_root / "drafts"
    ranked_root = round_root / "ranked"
    submission_root = round_root / "submission_pack"
    study_root = round_root / "study_remix"
    for path in (drafts_root, ranked_root, submission_root, study_root):
        path.mkdir(parents=True, exist_ok=True)

    submission_drafts = _build_submission_drafts(round_id, sound_ids, drafts_target)
    study_drafts = _build_optional_study_drafts(round_id, selected_count)
    all_drafts = submission_drafts + study_drafts
    for row in all_drafts:
        (drafts_root / f"{row['draft_id']}.json").write_text(json.dumps(row, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    ranked_submission = sorted(submission_drafts, key=lambda row: float(row.get("ranker_input_score", 0.0)), reverse=True)
    (ranked_root / "draft_candidates.json").write_text(json.dumps(submission_drafts, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (ranked_root / "ranked_submission_drafts.json").write_text(json.dumps(ranked_submission, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (study_root / "study_remix_drafts.json").write_text(json.dumps(study_drafts, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    submission_payload = {
        "round_id": round_id,
        "submission_drafts_count": len(submission_drafts),
        "selected_submission_draft_id": ranked_submission[0]["draft_id"] if ranked_submission else "",
        "synplant_included": False,
        "submission_safe": True,
        "manual_upload_required": True,
        "auto_submit_enabled": False,
        "files": {
            "midi_plan": "midi_plan.json",
            "arrangement_plan": "arrangement_plan.json",
            "render_plan": "render_plan.json",
            "submission_candidates": "ranked_submission_drafts.json",
        },
    }
    (submission_root / "midi_plan.json").write_text(json.dumps({"round_id": round_id, "draft_ids": [row["draft_id"] for row in submission_drafts]}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (submission_root / "arrangement_plan.json").write_text(json.dumps({"round_id": round_id, "notes": "manual arrangement review required"}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (submission_root / "render_plan.json").write_text(json.dumps({"round_id": round_id, "render_audio_locally": True, "upload_manually": True}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (submission_root / "submission_pack.json").write_text(json.dumps(submission_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    report = {
        "round_id": round_id,
        "drafts_generated": len(submission_drafts),
        "study_remix_drafts_generated": len(study_drafts),
        "output_root": round_root.as_posix(),
        "submission_pack_path": (submission_root / "submission_pack.json").as_posix(),
        "submission_allowed": False,
        "legal_sound_usage_only": True,
        "synplant_variations_excluded_from_submission": True,
        "blocker": "",
    }
    (project_root / "reports" / "beat_battle_agent" / f"{round_id}_round_beat_generation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    state = load_or_default_state(project_root / config.paths.local_state_path)
    state.drafts_generated += len(submission_drafts)
    save_state(project_root / config.paths.local_state_path, state)
    return report
