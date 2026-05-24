from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.local_rendering.midi_to_render_plan import build_render_plan_from_stems  # noqa: E402
from features.local_rendering.reaper_backend import load_local_render_config, run_reaper_auto_render  # noqa: E402
from features.local_rendering.render_plan_schema import render_plan_markdown, write_render_plan_json  # noqa: E402
from features.local_rendering.vst_registry_schema import load_registry  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Render local MIDI stems with Reaper (honest safe-fail mode).")
    parser.add_argument("generation_id", help="Generation id (folder under outputs/ and renders/).")
    parser.add_argument(
        "--stems-dir",
        default="",
        help="Optional stems directory. Default: outputs/<generation_id>/stems",
    )
    args = parser.parse_args()

    generation_id = args.generation_id
    stems_dir = Path(args.stems_dir) if args.stems_dir else (ROOT_DIR / "outputs" / generation_id / "stems")
    registry_path = ROOT_DIR / "config" / "local_vst_registry.local.json"
    local_config_path = ROOT_DIR / "config" / "local_render_config.local.json"

    registry = load_registry(registry_path)
    local_config = load_local_render_config(local_config_path)
    backend_name = str(local_config.get("default_render_backend", "dry_run_plan_only"))

    if not stems_dir.exists():
        raise FileNotFoundError(f"Missing stems dir: {stems_dir.as_posix()}")

    plan = build_render_plan_from_stems(
        generation_id=generation_id,
        stems_dir=stems_dir,
        registry=registry,
        default_backend=backend_name if backend_name in {"reaper_auto_render", "dry_run_plan_only"} else "dry_run_plan_only",
    )
    plan_path = ROOT_DIR / "outputs" / generation_id / "render_plan.json"
    plan_md = ROOT_DIR / "outputs" / generation_id / "render_plan.md"
    write_render_plan_json(plan_path, plan)
    plan_md.write_text(render_plan_markdown(plan), encoding="utf-8")

    report = run_reaper_auto_render(
        generation_id=generation_id,
        plan=plan,
        reaper_executable_path=str(local_config.get("reaper_executable_path", "")),
        vst_registry_configured=registry.configured,
        local_render_root=ROOT_DIR / "renders" / generation_id,
    )
    print(f"REAPER_RENDER_REPORT={ROOT_DIR.joinpath('reports', 'local_rendering', 'reaper_render_report.json').as_posix()}")
    print(f"REAPER_AVAILABLE={str(report.reaper_available).lower()}")
    print(f"WAV_RENDERED={str(report.wav_rendered).lower()}")
    print(f"RENDER_PLAN_ONLY={str(report.render_plan_only).lower()}")
    print(f"RENDER_BACKEND_STATUS={report.render_backend_status}")

    status_payload = {
        "generation_id": generation_id,
        "render_backend_status": report.render_backend_status,
        "reaper_available": report.reaper_available,
        "vst_registry_configured": report.vst_registry_configured,
        "wav_rendered": report.wav_rendered,
        "vst_render_used": report.vst_render_used,
        "fallback_preview_used": report.fallback_preview_used,
        "render_plan_only": report.render_plan_only,
    }
    (ROOT_DIR / "outputs" / generation_id / "render_status.json").write_text(
        json.dumps(status_payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
