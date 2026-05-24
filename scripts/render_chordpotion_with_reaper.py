from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.local_rendering.midi_fx_schema import MidiFxTransformPlan  # noqa: E402
from features.local_rendering.reaper_backend import run_chordpotion_reaper_render  # noqa: E402


def _read_plan(path: Path) -> MidiFxTransformPlan:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return MidiFxTransformPlan(
        generation_id=str(payload.get("generation_id", "")),
        input_harmony_midi=str(payload.get("input_harmony_midi", "")),
        input_bass_midi=str(payload.get("input_bass_midi", "")),
        input_lead_guide_midi=str(payload.get("input_lead_guide_midi", "")),
        output_transformed_midi=str(payload.get("output_transformed_midi", "")),
        bpm=int(payload.get("bpm", 100) or 100),
        midi_fx_role=str(payload.get("midi_fx_role", "chord_pattern_generator")),  # type: ignore[arg-type]
        midi_fx_plugin_id=str(payload.get("midi_fx_plugin_id", "")),
        chordpotion_configured=bool(payload.get("chordpotion_configured", False)),
        chordpotion_available=bool(payload.get("chordpotion_available", False)),
        reaper_available=bool(payload.get("reaper_available", False)),
        instrument_vst_available=bool(payload.get("instrument_vst_available", False)),
        transformed_midi_captured=bool(payload.get("transformed_midi_captured", False)),
        blocked=bool(payload.get("blocked", False)),
        blocked_reason=str(payload.get("blocked_reason", "")),
        missing_config=[str(x) for x in payload.get("missing_config", []) if str(x).strip()],
        planner_notes=[str(x) for x in payload.get("planner_notes", []) if str(x).strip()],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ChordPotion-oriented Reaper backend in safe, honest mode.")
    parser.add_argument("--generation-id", default="chordpotion_generation_v1")
    args = parser.parse_args()
    output_root = ROOT_DIR / "outputs" / args.generation_id
    plan_path = output_root / "chordpotion_transform_plan.json"
    if not plan_path.exists():
        raise FileNotFoundError(f"Missing transform plan: {plan_path.as_posix()}")

    report = run_chordpotion_reaper_render(
        generation_id=args.generation_id,
        transform_plan=_read_plan(plan_path),
        local_render_root=ROOT_DIR / "renders" / args.generation_id,
    )
    render_result = {
        "generation_id": args.generation_id,
        "chordpotion_configured": report.chordpotion_configured,
        "chordpotion_available": report.chordpotion_available,
        "reaper_available": report.reaper_available,
        "instrument_vst_available": report.instrument_vst_available,
        "transformed_midi_captured": report.transformed_midi_captured,
        "wav_rendered": report.wav_rendered,
        "final_wav_path": report.final_wav_path,
        "assisted_pack_path": report.assisted_pack_path,
        "missing_config": report.missing_config,
        "render_backend_status": report.render_backend_status,
    }
    if not report.wav_rendered:
        reason = report.missing_config[0] if report.missing_config else "render_not_executed"
        subprocess.run(
            [
                sys.executable,
                str(ROOT_DIR / "scripts" / "export_chordpotion_ableton_pack.py"),
                "--generation-id",
                args.generation_id,
                "--reason",
                reason,
            ],
            check=False,
            cwd=ROOT_DIR,
        )
    (output_root / "render_result.json").write_text(json.dumps(render_result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"WAV_RENDERED={str(report.wav_rendered).lower()}")
    print(f"TRANSFORMED_MIDI_CAPTURED={str(report.transformed_midi_captured).lower()}")
    print(f"ASSISTED_PACK={report.assisted_pack_path or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

