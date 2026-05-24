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


def analyze_manual_round_kit(project_root: Path) -> dict[str, Any]:
    manifest, blocker = _load_latest_manual_manifest(project_root)
    if manifest is None:
        return {"ok": False, "blocker": blocker}
    round_id = str(manifest.get("round_id", "")).strip()
    sounds = manifest.get("sounds", [])
    sounds = sounds if isinstance(sounds, list) else []
    total_bytes = sum(int(row.get("bytes", 0)) for row in sounds if isinstance(row, dict))
    analysis = {
        "round_id": round_id,
        "sounds_count": len(sounds),
        "total_bytes": total_bytes,
        "submission_safe_sounds_count": len([row for row in sounds if isinstance(row, dict) and row.get("submission_allowed") is True]),
        "study_only_sounds_count": len([row for row in sounds if isinstance(row, dict) and row.get("submission_allowed") is False]),
        "kit_density": "light" if len(sounds) < 8 else ("medium" if len(sounds) < 20 else "dense"),
        "blocker": "",
    }
    report_root = project_root / "reports" / "beat_battle_agent"
    report_root.mkdir(parents=True, exist_ok=True)
    (report_root / "round_kit_analysis.json").write_text(json.dumps(analysis, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (report_root / "round_kit_analysis.md").write_text(
        "\n".join(
            [
                "# Beat Battle Kit Analysis",
                "",
                f"- round_id: `{analysis['round_id']}`",
                f"- sounds_count: `{analysis['sounds_count']}`",
                f"- total_bytes: `{analysis['total_bytes']}`",
                f"- submission_safe_sounds_count: `{analysis['submission_safe_sounds_count']}`",
                f"- kit_density: `{analysis['kit_density']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"ok": True, **analysis}
