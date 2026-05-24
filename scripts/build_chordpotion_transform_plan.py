from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.local_rendering.chordpotion_transform_plan import (  # noqa: E402
    render_chordpotion_transform_plan_markdown,
    write_chordpotion_transform_plan,
)
from features.local_rendering.midi_fx_schema import MidiFxTransformPlan  # noqa: E402
from features.local_rendering.reaper_backend import load_local_render_config  # noqa: E402
from features.local_rendering.vst_registry_schema import load_registry  # noqa: E402


def _reaper_available(local_config: dict) -> bool:
    path = str(local_config.get("reaper_executable_path", ""))
    return bool(path and Path(path).exists())


def _instrument_vst_available(registry_configured: bool, registry) -> bool:
    if not registry_configured:
        return False
    return any(plugin.available and plugin.category != "midi_fx" for plugin in registry.plugins)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ChordPotion MIDI transform plan with honest local capability status.")
    parser.add_argument("--generation-id", default="chordpotion_generation_v1")
    args = parser.parse_args()

    output_root = ROOT_DIR / "outputs" / args.generation_id
    output_root.mkdir(parents=True, exist_ok=True)
    local_config = load_local_render_config(ROOT_DIR / "config" / "local_render_config.local.json")
    registry = load_registry(ROOT_DIR / "config" / "local_vst_registry.local.json")

    plugin_id = str(local_config.get("preferred_chordpotion_plugin_id", "")).strip() or str(
        local_config.get("chordpotion_plugin_id", "")
    ).strip()
    plugin = registry.get_plugin(plugin_id) if plugin_id else None
    if not plugin:
        for entry in registry.plugins:
            if entry.category == "midi_fx" and entry.display_name.lower() == "chordpotion":
                plugin = entry
                plugin_id = entry.plugin_id
                break
    chordpotion_configured = bool(plugin_id)
    chordpotion_available = bool(plugin and plugin.available and plugin.category == "midi_fx")
    reaper_available = _reaper_available(local_config)
    instrument_vst_available = _instrument_vst_available(registry.configured, registry)

    bpm = int(local_config.get("chordpotion_default_bpm", 100) or 100)
    if bpm <= 0:
        bpm = 100
    missing: list[str] = []
    if not chordpotion_configured:
        missing.append("preferred_chordpotion_plugin_id")
    if not chordpotion_available:
        missing.append("chordpotion_plugin_unavailable")
    if not reaper_available:
        missing.append("reaper_executable_path")
    if not instrument_vst_available:
        missing.append("instrument_vst_unavailable")

    blocked = len(missing) > 0
    blocked_reason = "local_requirements_missing" if blocked else ""
    plan = MidiFxTransformPlan(
        generation_id=args.generation_id,
        input_harmony_midi=(Path("outputs") / args.generation_id / "harmony_skeleton.mid").as_posix(),
        input_bass_midi=(Path("outputs") / args.generation_id / "bass.mid").as_posix(),
        input_lead_guide_midi=(Path("outputs") / args.generation_id / "lead_guide.mid").as_posix(),
        output_transformed_midi=(Path("outputs") / args.generation_id / "transformed_harmony.mid").as_posix(),
        bpm=bpm,
        midi_fx_role="chord_pattern_generator",
        midi_fx_plugin_id=plugin_id,
        chordpotion_configured=chordpotion_configured,
        chordpotion_available=chordpotion_available,
        reaper_available=reaper_available,
        instrument_vst_available=instrument_vst_available,
        transformed_midi_captured=False,
        blocked=blocked,
        blocked_reason=blocked_reason,
        missing_config=missing,
        planner_notes=[
            "Plan is local-only and does not assume plugin behavior unless verified available.",
            "If blocked=true, proceed with assisted DAW pack and manual plugin execution.",
        ],
    )
    write_chordpotion_transform_plan(output_root / "chordpotion_transform_plan.json", plan)
    (output_root / "chordpotion_transform_plan.md").write_text(
        render_chordpotion_transform_plan_markdown(plan),
        encoding="utf-8",
    )
    report_md = ROOT_DIR / "reports" / "local_rendering" / "chordpotion_transform_plan_report.md"
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(
        "\n".join(
            [
                "# ChordPotion Transform Plan Report",
                "",
                f"- chordpotion_configured: `{str(chordpotion_configured).lower()}`",
                f"- chordpotion_available: `{str(chordpotion_available).lower()}`",
                f"- reaper_available: `{str(reaper_available).lower()}`",
                f"- instrument_vst_available: `{str(instrument_vst_available).lower()}`",
                f"- blocked: `{str(blocked).lower()}`",
                f"- blocked_reason: `{blocked_reason or 'none'}`",
                "",
                "## Missing Config",
            ]
            + [f"- {item}" for item in missing]
            + [""],
        ),
        encoding="utf-8",
    )
    (output_root / "chordpotion_transform_plan_report.json").write_text(
        json.dumps(
            {
                "chordpotion_configured": chordpotion_configured,
                "chordpotion_available": chordpotion_available,
                "reaper_available": reaper_available,
                "instrument_vst_available": instrument_vst_available,
                "blocked": blocked,
                "blocked_reason": blocked_reason,
                "missing_config": missing,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"PLAN_JSON={(output_root / 'chordpotion_transform_plan.json').as_posix()}")
    print(f"CHORDPOTION_CONFIGURED={str(chordpotion_configured).lower()}")
    print(f"CHORDPOTION_AVAILABLE={str(chordpotion_available).lower()}")
    print(f"BLOCKED={str(blocked).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

