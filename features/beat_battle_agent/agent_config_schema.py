from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator


class BeatBattleAgentSafetyConfig(BaseModel):
    allow_captcha_bypass: bool = False
    allow_mfa_bypass: bool = False
    allow_login_bypass: bool = False
    allow_stealth_bot_evasion: bool = False
    allow_multi_account_farming: bool = False
    allow_scrape_unrelated_private_data: bool = False
    allow_spam_submissions: bool = False
    allow_fake_submissions_or_results: bool = False
    allow_fake_synplant_usage: bool = False
    allow_unauthorized_training_data: bool = False
    stop_on_login_required: bool = True
    stop_on_captcha_required: bool = True
    stop_on_manual_challenge_required: bool = True
    auto_submit: bool = False
    require_manual_submit_confirmation: bool = True

    @field_validator(
        "allow_captcha_bypass",
        "allow_mfa_bypass",
        "allow_login_bypass",
        "allow_stealth_bot_evasion",
        "allow_multi_account_farming",
        "allow_scrape_unrelated_private_data",
        "allow_spam_submissions",
        "allow_fake_submissions_or_results",
        "allow_fake_synplant_usage",
        "allow_unauthorized_training_data",
    )
    @classmethod
    def _disallow_unsafe_true_flags(cls, value: bool) -> bool:
        if value:
            raise ValueError("Unsafe beat-battle-agent bypass flags must remain false.")
        return value


class BeatBattleAgentPathsConfig(BaseModel):
    local_state_path: str = "battle_agent_state/agent_state.local.json"
    status_json_path: str = "reports/beat_battle_agent/agent_status.json"
    status_md_path: str = "reports/beat_battle_agent/agent_status.md"
    dashboard_json_path: str = "reports/beat_battle_agent/agent_dashboard.json"
    dashboard_md_path: str = "reports/beat_battle_agent/agent_dashboard.md"
    round_watcher_status_json_path: str = "reports/beat_battle_agent/round_watcher_status.json"
    round_watcher_status_md_path: str = "reports/beat_battle_agent/round_watcher_status.md"
    synplant_manifest_jsonl_path: str = "datasets/beat_battle_agent/synplant_variation_manifest.jsonl"
    local_synplant_variation_audio_root: str = "beat_battle_synplant_variations"
    round_outputs_root: str = "outputs/beat_battle_agent"
    results_dataset_jsonl_path: str = "datasets/beat_battle_agent/result_memory.jsonl"


class BeatBattleAgentConfig(BaseModel):
    enabled: bool = True
    site_config_path: str = "config/beat_battle_ranked_site.local.json"
    poll_interval_seconds: int = Field(default=120, ge=5, le=86_400)
    max_rounds_per_loop: int = Field(default=1, ge=1, le=100)
    min_drafts_per_round: int = Field(default=8, ge=8, le=128)
    max_synplant_variations_per_round: int = Field(default=12, ge=1, le=128)
    useful_variation_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    submission_allowed: bool = False
    safety: BeatBattleAgentSafetyConfig = Field(default_factory=BeatBattleAgentSafetyConfig)
    paths: BeatBattleAgentPathsConfig = Field(default_factory=BeatBattleAgentPathsConfig)


def load_agent_config(path: Path) -> BeatBattleAgentConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return BeatBattleAgentConfig.model_validate(payload)


def load_optional_local_agent_config(project_root: Path) -> tuple[BeatBattleAgentConfig | None, str | None]:
    local_path = project_root / "config" / "beat_battle_agent.local.json"
    if not local_path.exists():
        return None, "missing_local_agent_config"
    try:
        return load_agent_config(local_path), None
    except (ValidationError, json.JSONDecodeError):
        return None, "invalid_local_agent_config"


def config_to_public_dict(config: BeatBattleAgentConfig) -> dict[str, Any]:
    payload = config.model_dump(mode="json")
    payload["site_config_path"] = "config/beat_battle_ranked_site.local.json"
    payload["paths"]["local_state_path"] = "<LOCAL_STATE_PATH>"
    payload["paths"]["local_synplant_variation_audio_root"] = "<LOCAL_AUDIO_OUTPUT_ROOT>"
    return payload
