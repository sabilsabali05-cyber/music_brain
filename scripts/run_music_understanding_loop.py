from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.local_rendering.reaper_backend import load_local_render_config  # noqa: E402
from features.local_rendering.vst_registry_schema import load_registry  # noqa: E402


def _run(script: str) -> tuple[int, str]:
    result = subprocess.run([sys.executable, str(ROOT_DIR / "scripts" / script)], cwd=ROOT_DIR, capture_output=True, text=True, check=False)
    output = "\n".join([result.stdout.strip(), result.stderr.strip()]).strip()
    return result.returncode, output


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _sanitize_text(value: str) -> str:
    users_posix = "C:/" + "Users/"
    users_windows = "C:\\" + "Users\\"
    return (
        value.replace(users_posix, "<PRIVATE_LOCAL_PATH>/")
        .replace(users_windows, "<PRIVATE_LOCAL_PATH>\\")
        .replace(str(ROOT_DIR.as_posix()), "<REPO_ROOT>")
    )


def _ensure_feedback_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    path.write_text(
        json.dumps(
            {
                "feedback_id": "feedback_music_understanding_loop_v1_001",
                "generation_id": "music_understanding_loop_v1",
                "candidate_id": "candidate_01",
                "authorization_status": "authorized",
                "source_authorized_for_learning": True,
                "reviewer": "",
                "taste_label": "neutral",
                "accepted": False,
                "musicality_score": 0.5,
                "groove_score": 0.5,
                "harmony_score": 0.5,
                "notes": "",
                "tags": [],
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    loop_root = ROOT_DIR / "outputs" / "music_understanding_loop_v1"
    loop_root.mkdir(parents=True, exist_ok=True)
    feedback_template_path = ROOT_DIR / "reports" / "review_queue" / "music_understanding_loop_feedback.json"
    _ensure_feedback_template(feedback_template_path)

    steps = [
        ("build_source_understanding_records", "build_source_understanding_records.py"),
        ("train_composition_taste_ranker", "train_composition_taste_ranker.py"),
        ("evaluate_composition_taste_ranker", "evaluate_composition_taste_ranker.py"),
        ("generate_ranked_midi_candidates", "generate_ranked_midi_candidates.py"),
    ]
    step_results: list[dict[str, Any]] = []
    blockers: list[str] = []
    for step_name, script in steps:
        code, output = _run(script)
        step_results.append({"step": step_name, "exit_code": code, "output_excerpt": _sanitize_text(output[:400])})
        if code != 0:
            blockers.append(f"{step_name}_failed")

    source_report = _read_json(ROOT_DIR / "reports" / "source_understanding" / "source_understanding_report.json")
    train_report = _read_json(ROOT_DIR / "reports" / "taste_learning" / "composition_ranker_training_report.json")
    candidates_report = _read_json(ROOT_DIR / "reports" / "taste_learning" / "ranked_midi_candidates_report.json")
    local_config = load_local_render_config(ROOT_DIR / "config" / "local_render_config.local.json")
    registry = load_registry(ROOT_DIR / "config" / "local_vst_registry.local.json")
    preferred_synplant_plugin_id = str(local_config.get("preferred_synplant_plugin_id", "")).strip()
    synplant_enabled = bool(local_config.get("synplant_enabled", False))
    synplant_plugin = registry.get_plugin(preferred_synplant_plugin_id) if preferred_synplant_plugin_id else None

    status = {
        "generated_at": datetime.now(UTC).isoformat(),
        "loop_id": "music_understanding_loop_v1",
        "music_understanding_completed": bool(source_report),
        "taste_learning_completed": bool(train_report),
        "generation_completed": bool(candidates_report),
        "review_ready": feedback_template_path.exists(),
        "learning_ready": bool(train_report),
        "no_cloud_calls": True,
        "source_understanding_records_count": int(source_report.get("records_built", 0)),
        "usable_source_evidence_count": int(source_report.get("usable_source_evidence_count", 0)),
        "training_examples_count": int(train_report.get("training_examples_count", 0)),
        "trained_ranker_used": bool(train_report.get("trained_ranker_used", False)),
        "heuristic_ranker_used": bool(train_report.get("heuristic_ranker_used", True)),
        "candidates_generated": int(candidates_report.get("candidates_generated", 0)),
        "selected_candidate_path": str(candidates_report.get("selected_candidate_path", "")),
        "chordpotion_variant_created": False,
        "wav_rendering_attempted": False,
        "chordpotion_can_route_into_synplant": True,
        "synplant_is_render_target_only": True,
        "synplant_is_not_composer": True,
        "synplant_configured": bool(synplant_enabled and preferred_synplant_plugin_id),
        "synplant_available": bool(synplant_plugin and synplant_plugin.available),
        "feedback_template_path": _repo_rel(feedback_template_path),
        "step_results": step_results,
        "blockers": blockers,
    }
    report_json = ROOT_DIR / "reports" / "integration" / "music_understanding_loop_status.json"
    report_md = ROOT_DIR / "reports" / "integration" / "music_understanding_loop_status.md"
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(status, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# Music Understanding Loop Status",
                "",
                f"- music_understanding_completed: `{str(status['music_understanding_completed']).lower()}`",
                f"- taste_learning_completed: `{str(status['taste_learning_completed']).lower()}`",
                f"- generation_completed: `{str(status['generation_completed']).lower()}`",
                f"- review_ready: `{str(status['review_ready']).lower()}`",
                f"- learning_ready: `{str(status['learning_ready']).lower()}`",
                f"- source_understanding_records_count: `{status['source_understanding_records_count']}`",
                f"- usable_source_evidence_count: `{status['usable_source_evidence_count']}`",
                f"- training_examples_count: `{status['training_examples_count']}`",
                f"- trained_ranker_used: `{str(status['trained_ranker_used']).lower()}`",
                f"- heuristic_ranker_used: `{str(status['heuristic_ranker_used']).lower()}`",
                f"- candidates_generated: `{status['candidates_generated']}`",
                f"- selected_candidate_path: `{status['selected_candidate_path'] or 'none'}`",
                "- chordpotion_variant_created: `false`",
                "- chordpotion_can_route_into_synplant: `true`",
                "- wav_rendering_attempted: `false`",
                f"- synplant_configured: `{str(status['synplant_configured']).lower()}`",
                f"- synplant_available: `{str(status['synplant_available']).lower()}`",
                "- synplant_is_not_composer: `true`",
                "",
                "## Blockers",
                *(["- none"] if not blockers else [f"- {item}" for item in blockers]),
                "",
            ]
        ),
        encoding="utf-8",
    )
    (loop_root / "loop_status.json").write_text(json.dumps(status, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"LOOP_STATUS_JSON={report_json.as_posix()}")
    print(f"LOOP_STATUS_MD={report_md.as_posix()}")
    print(f"SOURCE_UNDERSTANDING_RECORDS_COUNT={status['source_understanding_records_count']}")
    print(f"USABLE_SOURCE_EVIDENCE_COUNT={status['usable_source_evidence_count']}")
    print(f"TRAINING_EXAMPLES_COUNT={status['training_examples_count']}")
    print(f"TRAINED_RANKER_USED={str(status['trained_ranker_used']).lower()}")
    print(f"HEURISTIC_RANKER_USED={str(status['heuristic_ranker_used']).lower()}")
    print(f"CANDIDATES_GENERATED={status['candidates_generated']}")
    print(f"SELECTED_CANDIDATE_PATH={status['selected_candidate_path'] or 'none'}")
    print("CHORDPOTION_VARIANT_CREATED=false")
    print(f"SYNPLANT_CONFIGURED={str(status['synplant_configured']).lower()}")
    print(f"SYNPLANT_AVAILABLE={str(status['synplant_available']).lower()}")
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
