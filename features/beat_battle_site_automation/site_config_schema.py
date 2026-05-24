from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator


class SessionConfig(BaseModel):
    headless: bool = False
    browser_channel: str = "chromium"
    storage_state_path: str = "config/beat_battle_ranked_site.session.local.json"
    manual_round_snapshot_path: str = "artifacts/beat_battle_site/manual_round_snapshot.json"
    manual_result_snapshot_path: str = "artifacts/beat_battle_site/manual_result_snapshot.json"


class SafetyConfig(BaseModel):
    allow_auto_submit: bool = False
    require_manual_submit_confirmation: bool = True
    allow_captcha_bypass: bool = False
    allow_login_bypass: bool = False
    allow_mfa_bypass: bool = False
    allow_bot_evasion: bool = False
    allow_multi_account: bool = False
    allow_fake_submission_claims: bool = False
    allow_fake_result_claims: bool = False
    allow_unrelated_private_data_scrape: bool = False
    allow_unauthorized_audio_training: bool = False

    @field_validator(
        "allow_captcha_bypass",
        "allow_login_bypass",
        "allow_mfa_bypass",
        "allow_bot_evasion",
        "allow_multi_account",
        "allow_fake_submission_claims",
        "allow_fake_result_claims",
        "allow_unrelated_private_data_scrape",
        "allow_unauthorized_audio_training",
    )
    @classmethod
    def _must_be_false(cls, value: bool) -> bool:
        if value:
            raise ValueError("Unsafe policy bypass flags must remain false.")
        return value


class SelectorsConfig(BaseModel):
    login_gate: str = "[data-test='login-required']"
    captcha_gate: str = "[data-test='captcha-required']"
    mfa_gate: str = "[data-test='mfa-required']"
    manual_confirmation_gate: str = "[data-test='manual-confirmation-required']"
    active_round_card: str = "[data-test='ranked-round-card']"
    active_round_id: str = "[data-test='round-id']"
    active_round_status: str = "[data-test='round-status']"
    active_round_sound_links: str = "[data-test='round-sound-link']"
    upload_input: str = "input[type='file']"
    submit_button: str = "[data-test='submit-entry']"
    result_row: str = "[data-test='my-result-row']"


class PathsConfig(BaseModel):
    local_raw_audio_dir: str = "datasets_local/beat_battle_site/raw_audio"
    local_render_dir: str = "renders/beat_battle_site"
    round_manifest_root: str = "datasets/beat_battle_site/rounds"
    round_results_jsonl: str = "datasets/beat_battle_site/results.jsonl"
    taste_feedback_jsonl: str = "datasets/taste_learning/beat_battle_site_feedback.jsonl"
    reports_root: str = "reports/beat_battle_site_automation"
    drafts_root: str = "outputs/beat_battle_site"


class RoundAcquisitionConfig(BaseModel):
    strategies: list[str] = Field(
        default_factory=lambda: [
            "snapshot_sound_links",
            "manual_file_import",
            "local_round_folder_scan",
        ]
    )
    manual_sound_file_paths: list[str] = Field(default_factory=list)
    local_round_sound_folder: str = "datasets_local/beat_battle_site/manual_round_sounds"


class BeatBattleRankedSiteConfig(BaseModel):
    site_name: str = "Beat Battle Ranked"
    base_url: str
    ranked_path: str
    user_handle: str
    session: SessionConfig = Field(default_factory=SessionConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    selectors: SelectorsConfig = Field(default_factory=SelectorsConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    acquisition: RoundAcquisitionConfig = Field(default_factory=RoundAcquisitionConfig)
    allow_synplant: bool = False
    allow_chordpotion: bool = False


def load_site_config(path: Path) -> BeatBattleRankedSiteConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return BeatBattleRankedSiteConfig.model_validate(payload)


def load_optional_local_site_config(project_root: Path) -> tuple[BeatBattleRankedSiteConfig | None, str | None]:
    local_path = project_root / "config" / "beat_battle_ranked_site.local.json"
    if not local_path.exists():
        return None, "missing_local_site_config"
    try:
        return load_site_config(local_path), None
    except (ValidationError, json.JSONDecodeError):
        return None, "invalid_local_site_config"


def config_to_public_dict(config: BeatBattleRankedSiteConfig) -> dict[str, Any]:
    payload = config.model_dump(mode="json")
    payload["session"]["storage_state_path"] = "<LOCAL_SESSION_STATE>"
    for idx, _ in enumerate(payload["acquisition"]["manual_sound_file_paths"]):
        payload["acquisition"]["manual_sound_file_paths"][idx] = "<LOCAL_AUDIO_PATH>"
    return payload
