from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_agent.compliance_policy import write_compliance_reports  # noqa: E402

MODE = "manual_or_authorized_only"


def _run(script_name: str) -> tuple[int, dict[str, str]]:
    command = [sys.executable, str(ROOT_DIR / "scripts" / script_name)]
    result = subprocess.run(command, cwd=ROOT_DIR, check=False, capture_output=True, text=True)
    parsed: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            parsed[key.strip()] = value.strip()
    return result.returncode, parsed


def _write_status_reports(payload: dict[str, object]) -> None:
    reports_root = ROOT_DIR / "reports" / "beat_battle_agent"
    reports_root.mkdir(parents=True, exist_ok=True)
    (reports_root / "study_agent_status.md").write_text(
        "\n".join(
            [
                "# Beat Battle Study Agent Status",
                "",
                f"- mode: `{payload['mode']}`",
                f"- blocker: `{payload['blocker'] or 'none'}`",
                f"- manual_round_import_ready: `{str(payload['manual_round_import_ready']).lower()}`",
                f"- sounds_imported: `{payload['sounds_imported']}`",
                f"- drafts_generated: `{payload['drafts_generated']}`",
                f"- submission_pack_path: `{payload['submission_pack_path']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_root / "battle_learning_status.md").write_text(
        "\n".join(
            [
                "# Beat Battle Learning Status",
                "",
                f"- result_logging_ready: `{str(payload['result_logging_ready']).lower()}`",
                f"- battle_outcome_ranker_status: `{payload['battle_outcome_ranker_status']}`",
                f"- results_logged: `{payload['results_logged']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_root / "synplant_catalog_status.md").write_text(
        "\n".join(
            [
                "# Synplant Catalog Status",
                "",
                f"- synplant_study_variations_generated: `{payload['synplant_study_variations_generated']}`",
                "- synplant_variations_submission_allowed: `false`",
                "- synplant_variations_study_allowed: `true`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_root / "study_agent_status.json").write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> int:
    compliance = write_compliance_reports(ROOT_DIR, mode=MODE)
    import_code, import_data = _run("import_beat_battle_manual_round.py")
    manual_round_import_ready = import_code == 0

    analysis_code, _ = _run("analyze_beat_battle_kit.py") if manual_round_import_ready else (1, {})
    draft_code, draft_data = _run("generate_beat_battle_drafts.py") if analysis_code == 0 else (1, {})
    synplant_code, synplant_data = _run("generate_synplant_study_variations.py") if analysis_code == 0 else (1, {})
    export_code, export_data = _run("export_beat_battle_submission_pack.py") if draft_code == 0 else (1, {})

    ingest_code, _ = _run("ingest_beat_battle_result.py")
    _run("analyze_battle_results.py")
    _run("train_battle_outcome_ranker.py")

    training_report_path = ROOT_DIR / "reports" / "beat_battle_agent" / "battle_outcome_ranker_training.json"
    training_mode = "heuristic_baseline"
    if training_report_path.exists():
        try:
            report_payload = json.loads(training_report_path.read_text(encoding="utf-8"))
            training_mode = str(report_payload.get("training_mode", "heuristic_baseline"))
        except json.JSONDecodeError:
            training_mode = "heuristic_baseline"

    blocker = ""
    if not manual_round_import_ready:
        blocker = import_data.get("BLOCKER", "missing_manual_round_config")

    results_count = 0
    results_path = ROOT_DIR / "datasets" / "beat_battle_agent" / "battle_results.jsonl"
    if results_path.exists():
        results_count = len([line for line in results_path.read_text(encoding="utf-8").splitlines() if line.strip()])

    payload: dict[str, object] = {
        "mode": MODE,
        "blocker": blocker,
        "live_site_automation_enabled": compliance["live_site_automation_enabled"],
        "manual_round_import_ready": manual_round_import_ready,
        "sounds_imported": int(import_data.get("SOUNDS_IMPORTED", "0") or 0),
        "drafts_generated": int(draft_data.get("DRAFTS_GENERATED", "0") or 0),
        "synplant_study_variations_generated": int(synplant_data.get("SYNPLANT_STUDY_VARIATIONS_GENERATED", "0") or 0),
        "submission_pack_path": export_data.get("SUBMISSION_PACK_PATH", ""),
        "result_logging_ready": ingest_code == 0,
        "results_logged": results_count,
        "battle_outcome_ranker_status": training_mode,
    }
    _write_status_reports(payload)
    print(f"BLOCKER={payload['blocker']}")
    print(f"MANUAL_ROUND_IMPORT_READY={str(payload['manual_round_import_ready']).lower()}")
    print(f"SOUNDS_IMPORTED={payload['sounds_imported']}")
    print(f"DRAFTS_GENERATED={payload['drafts_generated']}")
    print(f"SYNPLANT_STUDY_VARIATIONS_GENERATED={payload['synplant_study_variations_generated']}")
    print(f"SUBMISSION_PACK_PATH={payload['submission_pack_path']}")
    print(f"RESULT_LOGGING_READY={str(payload['result_logging_ready']).lower()}")
    print(f"BATTLE_OUTCOME_RANKER_STATUS={payload['battle_outcome_ranker_status']}")
    return 0 if blocker == "" else 1


if __name__ == "__main__":
    raise SystemExit(main())
