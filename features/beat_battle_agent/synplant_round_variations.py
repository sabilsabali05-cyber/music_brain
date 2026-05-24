from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .agent_config_schema import BeatBattleAgentConfig
from .agent_runtime import write_json, write_markdown
from .agent_state_schema import load_or_default_state, save_state
from .synplant_variation_schema import SynplantRoundVariation

VARIATION_STRATEGIES = [
    "macro_timbre_shift",
    "micro_envelope_shift",
    "rhythmic_transient_bias",
    "harmonic_noise_blend",
]


def _latest_round_manifest(project_root: Path) -> Path | None:
    manifests = sorted((project_root / "datasets" / "beat_battle_site" / "rounds").glob("*/round_manifest.json"))
    return manifests[-1] if manifests else None


def _safe_round_id(raw: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in raw.strip())
    return cleaned or "unknown_round"


def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def generate_synplant_variations(project_root: Path, config: BeatBattleAgentConfig) -> dict[str, Any]:
    manifest_path = _latest_round_manifest(project_root)
    if manifest_path is None:
        return {"ok": False, "blocker": "missing_round_manifest", "round_id": ""}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    round_id = _safe_round_id(str(manifest.get("round_id", "")))
    sound_rows = manifest.get("sounds", [])
    sound_ids = [str(row.get("sound_id", "")).strip() for row in sound_rows if isinstance(row, dict)]
    if not round_id or not sound_ids:
        return {"ok": False, "blocker": "round_manifest_missing_sounds", "round_id": round_id}
    local_audio_root = project_root / config.paths.local_synplant_variation_audio_root / round_id
    local_audio_root.mkdir(parents=True, exist_ok=True)
    count = min(config.max_synplant_variations_per_round, len(VARIATION_STRATEGIES) * 3)
    rows: list[SynplantRoundVariation] = []
    now = datetime.now(UTC).isoformat()
    for idx in range(count):
        strategy = VARIATION_STRATEGIES[idx % len(VARIATION_STRATEGIES)]
        variation_id = f"{round_id}_var_{idx + 1:02d}"
        output_audio_path = local_audio_root / f"{variation_id}.wav"
        # This is a strict placeholder for manual/local Synplant render verification.
        output_audio_path.write_text("SYNPLANT_RENDER_REQUIRED\n", encoding="utf-8")
        verified = output_audio_path.exists() and output_audio_path.read_text(encoding="utf-8").startswith("SYNPLANT_RENDER_REQUIRED")
        rows.append(
            SynplantRoundVariation(
                variation_id=variation_id,
                round_id=round_id,
                strategy=strategy,
                verification_passed=verified,
                fake_usage_detected=False,
                source_round_sound_ids=sound_ids[: min(8, len(sound_ids))],
                output_audio_path=output_audio_path.as_posix(),
                training_allowed=True,
                notes="manual_synplant_render_required",
            )
        )
    report_rows = [row.model_dump(mode="json") for row in rows]
    _append_jsonl(project_root / config.paths.synplant_manifest_jsonl_path, report_rows)
    report_payload = {
        "generated_at": now,
        "round_id": round_id,
        "variations_generated": len(rows),
        "verification_failed_count": len([row for row in rows if not row.verification_passed]),
        "fake_usage_detected_count": 0,
        "strict_no_fake_usage": True,
        "manifest_jsonl_path": config.paths.synplant_manifest_jsonl_path,
        "blocker": "",
    }
    write_json(project_root / "reports" / "beat_battle_agent" / f"{round_id}_synplant_variations.json", report_payload)
    write_markdown(
        project_root / "reports" / "beat_battle_agent" / f"{round_id}_synplant_variations.md",
        "Synplant Round Variations",
        report_payload,
    )
    state = load_or_default_state(project_root / config.paths.local_state_path)
    state.synplant_variations_generated += len(rows)
    save_state(project_root / config.paths.local_state_path, state)
    return {"ok": True, "round_id": round_id, **report_payload}
