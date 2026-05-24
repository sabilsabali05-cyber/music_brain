from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .render_plan_schema import RenderPlan

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


@dataclass
class AbletonAssistedReport:
    generation_id: str
    render_backend: str
    render_backend_status: str
    pack_path: str
    wav_rendered: bool
    vst_render_used: bool
    fallback_preview_used: bool
    render_plan_only: bool
    reason: str


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def create_ableton_assisted_render_pack(
    generation_id: str,
    stems_dir: Path,
    plan: RenderPlan,
    reason: str,
) -> AbletonAssistedReport:
    pack_root = ROOT_DIR / "outputs" / "render_ready_packs" / generation_id
    report_md = ROOT_DIR / "reports" / "local_rendering" / "ableton_render_report.md"
    pack_root.mkdir(parents=True, exist_ok=True)
    (pack_root / "midi_stems").mkdir(parents=True, exist_ok=True)

    for stem in stems_dir.glob("*.mid"):
        target = pack_root / "midi_stems" / stem.name
        target.write_bytes(stem.read_bytes())

    (pack_root / "render_plan.md").write_text(
        "\n".join(
            [
                "# Render Plan",
                "",
                f"- generation_id: `{generation_id}`",
                f"- default_backend: `{plan.default_render_backend}`",
                "",
                "## Stem Summary",
            ]
            + [
                f"- `{stem.track_name}` role=`{stem.track_role}` plugin=`{stem.suggested_plugin_id or 'none'}` "
                f"preset=`{stem.suggested_preset or 'none'}`"
                for stem in plan.stems
            ]
            + [""]
        ),
        encoding="utf-8",
    )
    (pack_root / "ableton_track_plan.md").write_text(
        "\n".join(
            [
                "# Ableton Track Plan",
                "",
                "Create one MIDI track per stem and assign local VSTs manually.",
                "Review gain staging and export master/stems manually.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pack_root / "vst_assignment.md").write_text(
        "\n".join(
            ["# VST Assignment", ""]
            + [
                f"- `{stem.track_name}` -> `{stem.suggested_plugin_id or 'unassigned'}` "
                f"(fallback category: `{stem.fallback_plugin_category}`)"
                for stem in plan.stems
            ]
            + [""]
        ),
        encoding="utf-8",
    )
    (pack_root / "texture_intent.md").write_text(
        "\n".join(
            ["# Texture Intent", ""] + [f"- `{stem.track_name}`: {stem.texture_intent}" for stem in plan.stems] + [""]
        ),
        encoding="utf-8",
    )
    (pack_root / "review_sheet.md").write_text(
        "\n".join(
            [
                "# Review Sheet",
                "",
                "- Verify plugin load and preset choice per track.",
                "- Verify no clipping on stems and master.",
                "- Export stems and final WAV manually.",
                "- Mark final decision and notes.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report = AbletonAssistedReport(
        generation_id=generation_id,
        render_backend="ableton_assisted_render",
        render_backend_status="assisted_pack_created",
        pack_path=_repo_relative(pack_root),
        wav_rendered=False,
        vst_render_used=False,
        fallback_preview_used=False,
        render_plan_only=True,
        reason=reason,
    )
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(
        "\n".join(
            [
                "# Ableton Assisted Render Report",
                "",
                f"- generation_id: `{generation_id}`",
                "- render_backend: `ableton_assisted_render`",
                "- render_backend_status: `assisted_pack_created`",
                "- wav_rendered: `false`",
                "- vst_render_used: `false`",
                "- fallback_preview_used: `false`",
                "- render_plan_only: `true`",
                f"- reason: `{reason}`",
                f"- pack_path: `{report.pack_path}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pack_root / "report.json").write_text(json.dumps(report.__dict__, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return report
