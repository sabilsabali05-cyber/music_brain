from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_latest_manual_manifest(project_root: Path) -> tuple[dict[str, Any] | None, str]:
    pointer = project_root / "datasets" / "beat_battle_agent" / "manual_rounds" / "latest_round_manifest.txt"
    if not pointer.exists():
        return None, "missing_manual_round_manifest"
    manifest_path = Path(pointer.read_text(encoding="utf-8").strip())
    if not manifest_path.is_absolute():
        manifest_path = (project_root / manifest_path).resolve()
    if not manifest_path.exists():
        return None, "missing_manual_round_manifest"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, "invalid_manual_round_manifest"
    if not isinstance(payload, dict):
        return None, "invalid_manual_round_manifest"
    return payload, ""


def generate_synplant_study_catalog(project_root: Path) -> dict[str, Any]:
    manifest, blocker = _load_latest_manual_manifest(project_root)
    if manifest is None:
        return {"ok": False, "blocker": blocker, "variations_generated": 0}
    round_id = str(manifest.get("round_id", "")).strip()
    sounds = manifest.get("sounds", [])
    sounds = sounds if isinstance(sounds, list) else []

    local_synplant_config = project_root / "config" / "synplant" / "synplant.local.json"
    local_synplant_enabled = local_synplant_config.exists()

    catalog_rows: list[dict[str, Any]] = []
    for sound_index, sound in enumerate(sounds, start=1):
        if not isinstance(sound, dict):
            continue
        sound_id = str(sound.get("sound_id", "")).strip()
        if not sound_id:
            continue
        for strategy in ("texture_shift", "harmonic_bloom", "transient_focus"):
            variation_id = f"{round_id}_{sound_index:02d}_{strategy}"
            output_audio_path = project_root / "beat_battle_synplant_variations" / round_id / f"{variation_id}.wav"
            catalog_rows.append(
                {
                    "variation_id": variation_id,
                    "round_id": round_id,
                    "source_sound_id": sound_id,
                    "strategy": strategy,
                    "task_type": "study_catalog",
                    "requested_generation": True,
                    "local_synplant_enabled": local_synplant_enabled,
                    "local_audio_expected_path": output_audio_path.as_posix(),
                    "local_audio_verified": output_audio_path.exists(),
                    "submission_allowed": False,
                    "study_allowed": True,
                    "notes": "study_only_not_submission_safe",
                }
            )

    datasets_root = project_root / "datasets" / "beat_battle_agent"
    datasets_root.mkdir(parents=True, exist_ok=True)
    catalog_jsonl = datasets_root / "synplant_study_catalog.jsonl"
    with catalog_jsonl.open("a", encoding="utf-8") as handle:
        for row in catalog_rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    report_root = project_root / "reports" / "beat_battle_agent"
    report_root.mkdir(parents=True, exist_ok=True)
    report = {
        "round_id": round_id,
        "synplant_study_variations_generated": len(catalog_rows),
        "local_synplant_enabled": local_synplant_enabled,
        "submission_allowed": False,
        "study_allowed": True,
        "catalog_path": catalog_jsonl.as_posix(),
        "blocker": "",
    }
    (report_root / "synplant_catalog_status.md").write_text(
        "\n".join(
            [
                "# Synplant Study Catalog Status",
                "",
                f"- round_id: `{round_id}`",
                f"- synplant_study_variations_generated: `{len(catalog_rows)}`",
                f"- local_synplant_enabled: `{str(local_synplant_enabled).lower()}`",
                "- submission_allowed: `false`",
                "- study_allowed: `true`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (report_root / "synplant_catalog_status.json").write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return {"ok": True, "blocker": "", "round_id": round_id, "variations_generated": len(catalog_rows), "local_synplant_enabled": local_synplant_enabled}
