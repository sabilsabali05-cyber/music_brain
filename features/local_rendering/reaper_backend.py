from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .render_plan_schema import RenderPlan

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


@dataclass
class ReaperRenderReport:
    generation_id: str
    render_backend: str
    render_backend_status: str
    reaper_available: bool
    vst_registry_configured: bool
    wav_rendered: bool
    vst_render_used: bool
    fallback_preview_used: bool
    render_plan_only: bool
    final_wav_path: str = ""
    stems_wav_paths: list[str] = field(default_factory=list)
    missing_config: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _write_markdown(path: Path, payload: ReaperRenderReport) -> None:
    lines = [
        "# Reaper Local Render Report",
        "",
        f"- generation_id: `{payload.generation_id}`",
        f"- render_backend: `{payload.render_backend}`",
        f"- render_backend_status: `{payload.render_backend_status}`",
        f"- reaper_available: `{payload.reaper_available}`",
        f"- vst_registry_configured: `{payload.vst_registry_configured}`",
        f"- wav_rendered: `{payload.wav_rendered}`",
        f"- vst_render_used: `{payload.vst_render_used}`",
        f"- fallback_preview_used: `{payload.fallback_preview_used}`",
        f"- render_plan_only: `{payload.render_plan_only}`",
        f"- final_wav_path: `{payload.final_wav_path or 'none'}`",
        "",
        "## Missing Config",
    ]
    lines.extend([f"- {item}" for item in payload.missing_config] or ["- none"])
    lines.extend(["", "## Notes"])
    lines.extend([f"- {item}" for item in payload.notes] or ["- none"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_reaper_auto_render(
    generation_id: str,
    plan: RenderPlan,
    reaper_executable_path: str,
    vst_registry_configured: bool,
    local_render_root: Path | None = None,
) -> ReaperRenderReport:
    local_render_root = local_render_root or (ROOT_DIR / "renders" / generation_id)
    stems_output = local_render_root / "stems"
    report_json = ROOT_DIR / "reports" / "local_rendering" / "reaper_render_report.json"
    report_md = ROOT_DIR / "reports" / "local_rendering" / "reaper_render_report.md"
    temp_project = local_render_root / "temp_reaper_project_plan.rpp.txt"
    final_wav = local_render_root / "final.wav"

    missing: list[str] = []
    reaper_available = False
    if not reaper_executable_path:
        missing.append("reaper_executable_path")
    else:
        reaper_available = Path(reaper_executable_path).exists()
        if not reaper_available:
            missing.append("reaper_executable_path_not_found")
    if not vst_registry_configured:
        missing.append("local_vst_registry.local.json_missing_or_empty")

    stems_output.mkdir(parents=True, exist_ok=True)
    local_render_root.mkdir(parents=True, exist_ok=True)

    if missing:
        status = "planned_not_executed"
        notes = [
            "Safe-fail path triggered; no misleading WAV claim was made.",
            "Generated actionable project plan text for manual DAW execution.",
        ]
    else:
        # CLI automation is represented as planned scaffolding in this version.
        status = "planned_not_executed"
        notes = [
            "Reaper executable and registry detected, but full CLI automation is not yet implemented.",
            "Use generated project plan to execute render manually in Reaper.",
        ]
    temp_project.write_text(
        "\n".join(
            [
                f"generation_id={generation_id}",
                f"render_backend=reaper_auto_render",
                f"stems_count={len(plan.stems)}",
                "action=import_midi_assign_plugins_render_master_and_stems",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    wav_exists = final_wav.exists() and final_wav.is_file() and final_wav.stat().st_size > 0
    report = ReaperRenderReport(
        generation_id=generation_id,
        render_backend="reaper_auto_render",
        render_backend_status=status,
        reaper_available=reaper_available,
        vst_registry_configured=vst_registry_configured,
        wav_rendered=wav_exists,
        vst_render_used=wav_exists and vst_registry_configured,
        fallback_preview_used=False,
        render_plan_only=not wav_exists,
        final_wav_path=_repo_relative(final_wav) if wav_exists else "",
        stems_wav_paths=[],
        missing_config=missing,
        notes=notes,
    )

    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    _write_markdown(report_md, report)
    return report


def load_local_render_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}
