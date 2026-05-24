from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .site_config_schema import BeatBattleRankedSiteConfig


@dataclass(frozen=True)
class SubmissionRenderResult:
    rendered_submission_available: bool
    round_id: str
    render_target_wav: str
    render_target_mp3: str
    blocker: str | None
    notes: list[str]


def render_submission(
    *,
    config: BeatBattleRankedSiteConfig,
    project_root: Path,
    round_id: str,
    selected_draft_path: Path,
) -> SubmissionRenderResult:
    local_render_root = (project_root / config.paths.local_render_dir / round_id).resolve()
    local_render_root.mkdir(parents=True, exist_ok=True)
    wav_path = local_render_root / "submission.wav"
    mp3_path = local_render_root / "submission.mp3"
    if not selected_draft_path.exists():
        return SubmissionRenderResult(
            rendered_submission_available=False,
            round_id=round_id,
            render_target_wav=wav_path.as_posix(),
            render_target_mp3=mp3_path.as_posix(),
            blocker="missing_selected_draft",
            notes=["Cannot render without selected draft."],
        )
    return SubmissionRenderResult(
        rendered_submission_available=False,
        round_id=round_id,
        render_target_wav=wav_path.as_posix(),
        render_target_mp3=mp3_path.as_posix(),
        blocker="manual_render_required",
        notes=[
            "Renderer intentionally does not fake audio exports.",
            "Provide manual local render output to continue submission.",
        ],
    )


def as_dict(result: SubmissionRenderResult) -> dict[str, Any]:
    return {
        "rendered_submission_available": result.rendered_submission_available,
        "round_id": result.round_id,
        "render_target_wav": result.render_target_wav,
        "render_target_mp3": result.render_target_mp3,
        "blocker": result.blocker,
        "notes": result.notes,
    }
