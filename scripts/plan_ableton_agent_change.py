from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.ableton_agent import (  # noqa: E402
    AbletonIntent,
    AbletonProjectState,
    ArrangementSection,
    ClipState,
    DeviceState,
    TrackState,
    build_ableton_change_plan,
)

REPORT_DIR = ROOT_DIR / "reports" / "ableton_agent"
PLAN_JSON = "ableton_agent_change_plan.json"
PLAN_MD = "ableton_agent_change_plan.md"


def build_sample_intent() -> AbletonIntent:
    return AbletonIntent(
        intent_id="sample_bridge_intent",
        prompt="Add a generated bridge and smooth transition before final chorus.",
        goal="Increase contrast and lift before the ending chorus.",
        preferred_sections=["bridge", "chorus_2"],
        constraints=[
            "dry-run by default",
            "no GUI automation",
            "no real Ableton mutation",
        ],
        generated_candidates_requested=["bridge_candidate_001"],
        notes="Generated outputs remain candidates until human approval.",
    )


def build_mock_project_state() -> AbletonProjectState:
    return AbletonProjectState(
        tempo=124.0,
        time_signature="4/4",
        arrangement_sections=[
            ArrangementSection(section_id="sec_intro", label="intro", start_bar=1, end_bar=16),
            ArrangementSection(section_id="sec_verse", label="verse", start_bar=17, end_bar=48),
            ArrangementSection(section_id="sec_bridge", label="bridge", start_bar=49, end_bar=64),
            ArrangementSection(section_id="sec_chorus2", label="chorus_2", start_bar=65, end_bar=96),
        ],
        tracks=[
            TrackState(track_id="trk_1", track_name="Drums", track_type="midi"),
            TrackState(track_id="trk_2", track_name="Bass", track_type="midi"),
            TrackState(track_id="trk_3", track_name="Pads", track_type="midi"),
        ],
        clips=[
            ClipState(clip_id="clip_1", track_id="trk_2", section_id="sec_verse", start_bar=17, end_bar=32),
            ClipState(clip_id="clip_2", track_id="trk_3", section_id="sec_chorus2", start_bar=65, end_bar=96),
        ],
        devices=[
            DeviceState(device_id="dev_1", track_id="trk_3", device_name="Auto Filter", parameters=["Cutoff", "Resonance"]),
        ],
        parameters=["Cutoff", "Resonance", "Volume", "Pan"],
        automation_lanes=["trk_3.Auto Filter.Cutoff"],
        markers=["intro_start", "chorus_2_start"],
        key_harmony_estimate="A minor",
        density_estimate="medium-high",
        available_generated_candidates=[
            {
                "candidate_id": "bridge_candidate_001",
                "source": "symbolic-model-placeholder",
                "status": "generated_candidate",
                "provenance_ref": "generated_candidate://bridge_candidate_001",
            }
        ],
        human_review_notes=["Bridge should avoid masking vocal lead."],
    )


def build_change_plan_payload() -> dict[str, Any]:
    intent = build_sample_intent()
    project_state = build_mock_project_state()
    plan = build_ableton_change_plan(intent, project_state)
    return {
        "status": "planned_dry_run_only",
        "hard_constraints_respected": True,
        "dry_run_default": True,
        "ableton_connected": False,
        "live_set_modified": False,
        "commands_generated": True,
        "commands_executed": False,
        "human_review_required": True,
        "model_generation_performed": False,
        "audio_processing_performed": False,
        "training_performed": False,
        "intent": intent.to_dict(),
        "project_state_summary": {
            "tempo": project_state.tempo,
            "time_signature": project_state.time_signature,
            "section_count": len(project_state.arrangement_sections),
            "track_count": len(project_state.tracks),
            "candidate_count": len(project_state.available_generated_candidates),
        },
        **plan.to_dict(),
        "limitations": [
            "No Ableton API control is implemented in this scaffold.",
            "No model generation, audio processing, or training is performed.",
            "No GUI automation is used.",
        ],
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Ableton Agent Change Plan",
        "",
        f"- status: `{payload['status']}`",
        f"- ableton_connected: `{payload['ableton_connected']}`",
        f"- live_set_modified: `{payload['live_set_modified']}`",
        f"- commands_generated: `{payload['commands_generated']}`",
        f"- commands_executed: `{payload['commands_executed']}`",
        f"- human_review_required: `{payload['human_review_required']}`",
        "",
        "## Interpreted Musical Intent",
        f"- {payload['interpreted_musical_intent']}",
        "",
        "## Proposed Arrangement Changes",
    ]
    lines.extend([f"- {item}" for item in payload["proposed_arrangement_changes"]])
    lines.extend(["", "## Proposed Generated Candidates Needed"])
    lines.extend([f"- `{item['candidate_id']}` ({item['status']})" for item in payload["proposed_generated_candidates_needed"]])
    lines.extend(["", "## Proposed Ableton Commands"])
    lines.extend([f"- `{cmd['command_type']}` review_required=`{cmd['human_review_required']}`" for cmd in payload["proposed_ableton_commands"]])
    lines.extend(["", "## Risk Warnings"])
    lines.extend([f"- {item}" for item in payload["risk_warnings"]])
    lines.append("")
    return "\n".join(lines)


def write_change_plan_report(output_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    payload = build_change_plan_payload()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PLAN_JSON
    md_path = output_dir / PLAN_MD
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(payload), encoding="utf-8")
    return json_path, md_path, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Ableton Agent bridge change plan (dry-run scaffold only).")
    parser.add_argument("--output-dir", default=REPORT_DIR.as_posix())
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    json_path, md_path, payload = write_change_plan_report(output_dir)
    print(f"ABLETON_AGENT_CHANGE_PLAN_JSON={json_path.as_posix()}")
    print(f"ABLETON_AGENT_CHANGE_PLAN_MD={md_path.as_posix()}")
    print(f"ABLETON_CONNECTED={payload['ableton_connected']}")
    print(f"LIVE_SET_MODIFIED={payload['live_set_modified']}")
    print(f"COMMANDS_GENERATED={payload['commands_generated']}")
    print(f"COMMANDS_EXECUTED={payload['commands_executed']}")
    print(f"HUMAN_REVIEW_REQUIRED={payload['human_review_required']}")
    print("MODEL_GENERATION_PERFORMED=False")
    print("AUDIO_PROCESSING_PERFORMED=False")
    print("TRAINING_PERFORMED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
