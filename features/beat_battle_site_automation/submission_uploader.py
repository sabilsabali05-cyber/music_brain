from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .site_config_schema import BeatBattleRankedSiteConfig


@dataclass(frozen=True)
class SubmissionResult:
    upload_success: bool
    submitted: bool
    stopped_pre_submit: bool
    blocker: str | None
    status: str
    require_manual_submit_confirmation: bool
    allow_auto_submit: bool


def submit_entry(
    *,
    config: BeatBattleRankedSiteConfig,
    render_path: Path,
    manual_submit_confirmed: bool = False,
) -> SubmissionResult:
    if not render_path.exists():
        return SubmissionResult(
            upload_success=False,
            submitted=False,
            stopped_pre_submit=True,
            blocker="missing_rendered_submission",
            status="blocked_missing_rendered_submission",
            require_manual_submit_confirmation=config.safety.require_manual_submit_confirmation,
            allow_auto_submit=config.safety.allow_auto_submit,
        )
    if config.safety.require_manual_submit_confirmation and not manual_submit_confirmed:
        return SubmissionResult(
            upload_success=False,
            submitted=False,
            stopped_pre_submit=True,
            blocker="manual_submit_confirmation_required",
            status="stopped_pre_submit_manual_confirmation_required",
            require_manual_submit_confirmation=True,
            allow_auto_submit=config.safety.allow_auto_submit,
        )
    if not config.safety.allow_auto_submit:
        return SubmissionResult(
            upload_success=False,
            submitted=False,
            stopped_pre_submit=True,
            blocker="auto_submit_disabled",
            status="stopped_pre_submit_auto_submit_disabled",
            require_manual_submit_confirmation=config.safety.require_manual_submit_confirmation,
            allow_auto_submit=False,
        )
    return SubmissionResult(
        upload_success=True,
        submitted=True,
        stopped_pre_submit=False,
        blocker=None,
        status="submitted",
        require_manual_submit_confirmation=config.safety.require_manual_submit_confirmation,
        allow_auto_submit=config.safety.allow_auto_submit,
    )


def as_dict(result: SubmissionResult) -> dict[str, Any]:
    return {
        "upload_success": result.upload_success,
        "submitted": result.submitted,
        "stopped_pre_submit": result.stopped_pre_submit,
        "blocker": result.blocker,
        "status": result.status,
        "require_manual_submit_confirmation": result.require_manual_submit_confirmation,
        "allow_auto_submit": result.allow_auto_submit,
    }
