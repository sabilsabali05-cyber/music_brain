from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_site_automation.site_config_schema import BeatBattleRankedSiteConfig, load_optional_local_site_config  # noqa: E402

STATUS_PROCESSING = "processing_round"
STATUS_WAITING_SUBMIT = "waiting_for_manual_submission"
STATUS_WAITING_RESULT = "waiting_for_result_entry"
STATUS_TRAINING_READY = "training_ready"
STATUS_TRAINING_SKIPPED = "training_skipped"

ALLOWED_AUTH = {"authorized", "public_domain", "self_owned"}
TRAINING_THRESHOLD = 20
AUDIO_EXTENSIONS = {".wav", ".mp3", ".aif", ".aiff", ".flac", ".ogg", ".m4a"}

ScriptRunner = Callable[[Path, str, list[str]], tuple[int, str]]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _write_status_reports(project_root: Path, payload: dict[str, Any]) -> None:
    report_root = project_root / "reports" / "beat_battle_site_automation"
    report_json = report_root / "session_loop_status.json"
    report_md = report_root / "session_loop_status.md"
    report_root.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Beat Battle Session Loop Status",
        "",
        f"- status: `{payload.get('status', 'unknown')}`",
        f"- round_id: `{payload.get('round_id', 'unknown')}`",
        f"- next_action: `{payload.get('next_action', 'none')}`",
        f"- blocker: `{payload.get('blocker', 'none')}`",
        f"- training_threshold: `{payload.get('training_threshold', TRAINING_THRESHOLD)}`",
        f"- authorized_feedback_count: `{payload.get('authorized_feedback_count', 0)}`",
        f"- mode: `{payload.get('mode', 'once')}`",
        "",
        "## Status History",
    ]
    for row in payload.get("status_history", []):
        if not isinstance(row, dict):
            continue
        lines.append(f"- `{row.get('status', 'unknown')}`: {row.get('message', '')}")
    lines.append("")
    report_md.write_text("\n".join(lines), encoding="utf-8")


def _run_script(project_root: Path, script_name: str, args: list[str]) -> tuple[int, str]:
    command = [sys.executable, str(project_root / "scripts" / script_name), *args]
    result = subprocess.run(command, cwd=project_root, capture_output=True, text=True, check=False)
    output = "\n".join([result.stdout.strip(), result.stderr.strip()]).strip()
    return result.returncode, output


def _append_status(payload: dict[str, Any], status: str, message: str, *, next_action: str = "", blocker: str = "") -> None:
    payload["status"] = status
    payload["next_action"] = next_action
    payload["blocker"] = blocker
    payload.setdefault("status_history", []).append({"timestamp": _now_iso(), "status": status, "message": message})


def _detect_latest_local_round_id(config: BeatBattleRankedSiteConfig, project_root: Path) -> str:
    rounds_root = (project_root / config.acquisition.local_round_sound_folder).resolve()
    if not rounds_root.exists():
        return ""
    candidates: list[tuple[float, str]] = []
    for child in rounds_root.iterdir():
        if not child.is_dir():
            continue
        has_audio = any(item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS for item in child.iterdir())
        if not has_audio:
            continue
        candidates.append((child.stat().st_mtime, child.name))
    if not candidates:
        return ""
    candidates.sort(key=lambda row: row[0], reverse=True)
    return candidates[0][1]


def _import_round_snapshot(config: BeatBattleRankedSiteConfig, project_root: Path, round_id: str) -> Path:
    snapshot_path = (project_root / config.session.manual_round_snapshot_path).resolve()
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _read_json(snapshot_path)
    round_cards = payload.get("round_cards")
    if not isinstance(round_cards, list):
        round_cards = []
    updated_round_cards = [
        {
            "round_id": round_id,
            "status": "active",
            "sound_urls": [],
        }
    ]
    payload.update(
        {
            "active_round_id": round_id,
            "active_round_sound_urls": [],
            "round_cards": updated_round_cards,
        }
    )
    snapshot_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return snapshot_path


def _count_authorized_feedback(feedback_path: Path) -> int:
    count = 0
    for row in _read_jsonl_rows(feedback_path):
        auth = str(row.get("authorization_status", "")).strip().lower()
        if auth not in ALLOWED_AUTH:
            continue
        if not bool(row.get("source_authorized_for_learning", False)):
            continue
        if "result_available" in row and not bool(row.get("result_available", False)):
            continue
        count += 1
    return count


def _write_result_analysis(config: BeatBattleRankedSiteConfig, project_root: Path, round_id: str) -> dict[str, Any]:
    results_path = (project_root / config.paths.round_results_jsonl).resolve()
    rows = _read_jsonl_rows(results_path)
    matching = [row for row in rows if str(row.get("round_id", "")).strip() == round_id]
    placements: list[int] = []
    for row in matching:
        try:
            placements.append(int(row.get("placement")))
        except Exception:  # noqa: BLE001
            continue
    payload = {
        "round_id": round_id,
        "total_results_logged": len(rows),
        "round_results_logged": len(matching),
        "best_placement_for_round": min(placements) if placements else None,
        "average_placement_for_round": round(sum(placements) / len(placements), 3) if placements else None,
        "analysis_generated_at": _now_iso(),
    }
    report_root = project_root / "reports" / "beat_battle_site_automation"
    report_root.mkdir(parents=True, exist_ok=True)
    (report_root / "battle_result_analysis_report.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    md_lines = [
        "# Beat Battle Result Analysis Report",
        "",
        f"- round_id: `{round_id}`",
        f"- total_results_logged: `{payload['total_results_logged']}`",
        f"- round_results_logged: `{payload['round_results_logged']}`",
        f"- best_placement_for_round: `{payload['best_placement_for_round']}`",
        f"- average_placement_for_round: `{payload['average_placement_for_round']}`",
        "",
    ]
    (report_root / "battle_result_analysis_report.md").write_text("\n".join(md_lines), encoding="utf-8")
    return payload


def _run_training_if_ready(
    *,
    config: BeatBattleRankedSiteConfig,
    project_root: Path,
    payload: dict[str, Any],
    run_script: ScriptRunner,
) -> None:
    feedback_path = (project_root / config.paths.taste_feedback_jsonl).resolve()
    authorized_count = _count_authorized_feedback(feedback_path)
    payload["authorized_feedback_count"] = authorized_count
    payload["training_threshold"] = TRAINING_THRESHOLD
    if authorized_count < TRAINING_THRESHOLD:
        _append_status(
            payload,
            STATUS_TRAINING_SKIPPED,
            "Skipped ranker training because feedback threshold is not met.",
            next_action=f"Add more authorized results ({authorized_count}/{TRAINING_THRESHOLD}) then rerun.",
        )
        return

    site_code, site_out = run_script(project_root, "train_beat_battle_site_ranker.py", [])
    comp_code, comp_out = run_script(project_root, "train_composition_taste_ranker.py", [])
    payload["training_runs"] = [
        {"script": "train_beat_battle_site_ranker.py", "exit_code": site_code, "output_excerpt": site_out[:300]},
        {"script": "train_composition_taste_ranker.py", "exit_code": comp_code, "output_excerpt": comp_out[:300]},
    ]
    _append_status(
        payload,
        STATUS_TRAINING_READY,
        "Ranker training threshold met and training executed.",
        next_action="Review training reports and continue to next round.",
        blocker="" if site_code == 0 and comp_code == 0 else "ranker_training_failed",
    )


def _run_round_pipeline(
    *,
    project_root: Path,
    config: BeatBattleRankedSiteConfig,
    round_id: str,
    run_script: ScriptRunner,
    payload: dict[str, Any],
) -> tuple[bool, str]:
    _append_status(
        payload,
        STATUS_PROCESSING,
        "Running round pipeline.",
        next_action="Waiting for automated steps to complete.",
    )
    _write_status_reports(project_root, payload)

    steps: list[tuple[str, str, list[str]]] = [
        ("detect", "detect_beat_battle_round.py", []),
        ("acquire", "acquire_beat_battle_round_sounds.py", []),
        ("analyze", "analyze_beat_battle_kit.py", []),
        ("drafts", "generate_beat_battle_drafts.py", []),
        ("sound_pairs", "create_battle_sound_pair_record.py", ["--manifest", f"datasets/beat_battle_site/rounds/{round_id}/round_manifest.json"]),
        ("render", "render_beat_battle_submission.py", []),
        ("submit", "submit_beat_battle_entry.py", []),
    ]
    step_results: list[dict[str, Any]] = []
    submission_status = ""
    for name, script, args in steps:
        code, output = run_script(project_root, script, args)
        step_results.append({"step": name, "script": script, "exit_code": code, "output_excerpt": output[:300]})
        if name == "submit":
            submission_status = str(_read_json(project_root / "reports" / "beat_battle_site_automation" / "submission_report.json").get("status", ""))
    payload["step_results"] = step_results
    if submission_status.startswith("stopped_pre_submit"):
        _append_status(
            payload,
            STATUS_WAITING_SUBMIT,
            "Submission pack exported. Manual site submission required.",
            next_action="Submit the rendered entry on the site, then fill manual result snapshot locally.",
        )
        _write_status_reports(project_root, payload)
        return False, STATUS_WAITING_SUBMIT
    if submission_status == "submitted":
        _append_status(
            payload,
            STATUS_WAITING_RESULT,
            "Submission recorded. Waiting for manual result entry.",
            next_action="Enter round result in manual result snapshot once available.",
        )
        _write_status_reports(project_root, payload)
        return True, STATUS_WAITING_RESULT

    _append_status(
        payload,
        STATUS_WAITING_SUBMIT,
        "Submission status unclear; waiting for manual submit/result entry.",
        next_action="Manually submit and ensure result snapshot is updated.",
        blocker="submission_status_unknown",
    )
    _write_status_reports(project_root, payload)
    return False, STATUS_WAITING_SUBMIT


def run_session_once(
    *,
    project_root: Path,
    poll_seconds: int,
    max_wait_seconds: int,
    wait_for_result_after_manual_submit: bool = False,
    mode: str = "once",
    run_script: ScriptRunner = _run_script,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> int:
    config, blocker = load_optional_local_site_config(project_root)
    payload: dict[str, Any] = {
        "generated_at": _now_iso(),
        "mode": mode,
        "round_id": "",
        "status": STATUS_PROCESSING,
        "next_action": "",
        "blocker": "",
        "status_history": [],
        "training_threshold": TRAINING_THRESHOLD,
        "authorized_feedback_count": 0,
    }
    if config is None:
        _append_status(
            payload,
            STATUS_PROCESSING,
            "Cannot start: missing local site config.",
            next_action="Create config/beat_battle_ranked_site.local.json and rerun.",
            blocker=blocker or "missing_local_site_config",
        )
        _write_status_reports(project_root, payload)
        return 1

    round_id = _detect_latest_local_round_id(config, project_root)
    if not round_id:
        _append_status(
            payload,
            STATUS_PROCESSING,
            "No manual round folder found.",
            next_action=f"Create {config.acquisition.local_round_sound_folder}/<round_id> with kit sounds.",
            blocker="missing_manual_round_folder",
        )
        _write_status_reports(project_root, payload)
        return 1

    _import_round_snapshot(config, project_root, round_id)
    payload["round_id"] = round_id
    expects_result, pipeline_status = _run_round_pipeline(
        project_root=project_root,
        config=config,
        round_id=round_id,
        run_script=run_script,
        payload=payload,
    )
    if not expects_result and pipeline_status == STATUS_WAITING_SUBMIT:
        if not wait_for_result_after_manual_submit:
            return 0

    start = time.monotonic()
    while True:
        snapshot = _read_json((project_root / config.session.manual_result_snapshot_path).resolve())
        snapshot_round = str(snapshot.get("round_id", "")).strip()
        result_available = bool(snapshot.get("result_available", False))
        if snapshot_round == round_id and result_available:
            break
        if snapshot_round == round_id and not result_available:
            _append_status(
                payload,
                STATUS_WAITING_RESULT,
                "Result snapshot found but result not available yet.",
                next_action="Update result_available=true after official result appears.",
            )
        else:
            _append_status(
                payload,
                STATUS_WAITING_SUBMIT,
                "Waiting for manual submission/result entry files.",
                next_action="Submit manually, then update manual result snapshot for this round.",
            )
        _write_status_reports(project_root, payload)
        if max_wait_seconds > 0 and (time.monotonic() - start) >= max_wait_seconds:
            return 0
        sleep_fn(float(max(poll_seconds, 1)))

    run_script(project_root, "check_beat_battle_result.py", [])
    _write_result_analysis(config, project_root, round_id)
    _run_training_if_ready(config=config, project_root=project_root, payload=payload, run_script=run_script)
    _write_status_reports(project_root, payload)
    return 0 if not payload.get("blocker") else 1


def run_session_watch(
    *,
    project_root: Path,
    poll_seconds: int,
    run_script: ScriptRunner = _run_script,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> int:
    config, blocker = load_optional_local_site_config(project_root)
    payload: dict[str, Any] = {
        "generated_at": _now_iso(),
        "mode": "watch",
        "round_id": "",
        "status": STATUS_PROCESSING,
        "next_action": "",
        "blocker": "",
        "status_history": [],
        "training_threshold": TRAINING_THRESHOLD,
        "authorized_feedback_count": 0,
    }
    if config is None:
        _append_status(
            payload,
            STATUS_PROCESSING,
            "Cannot start watcher: missing local site config.",
            next_action="Create config/beat_battle_ranked_site.local.json and rerun watcher.",
            blocker=blocker or "missing_local_site_config",
        )
        _write_status_reports(project_root, payload)
        return 1

    last_round_id = ""
    while True:
        round_id = _detect_latest_local_round_id(config, project_root)
        if not round_id:
            _append_status(
                payload,
                STATUS_PROCESSING,
                "Watcher polling for new round folders.",
                next_action=f"Add a new folder under {config.acquisition.local_round_sound_folder} to start automation.",
            )
            _write_status_reports(project_root, payload)
            sleep_fn(float(max(poll_seconds, 1)))
            continue
        if round_id != last_round_id:
            _import_round_snapshot(config, project_root, round_id)
            payload["round_id"] = round_id
            run_session_once(
                project_root=project_root,
                poll_seconds=poll_seconds,
                max_wait_seconds=0,
                wait_for_result_after_manual_submit=True,
                mode="watch",
                run_script=run_script,
                sleep_fn=sleep_fn,
            )
            last_round_id = round_id
        sleep_fn(float(max(poll_seconds, 1)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run high-automation Beat Battle session loop.")
    parser.add_argument("--watch", action="store_true", help="Continuously poll for new round folders.")
    parser.add_argument("--poll-seconds", type=int, default=10, help="Polling interval for watcher/manual result checks.")
    parser.add_argument(
        "--max-wait-seconds",
        type=int,
        default=0,
        help="When >0, keep waiting for manual result entry up to this duration in one-shot mode.",
    )
    parser.add_argument(
        "--wait-for-result-entry",
        action="store_true",
        help="In one-shot mode, keep polling for manual result entry after manual submission is required.",
    )
    args = parser.parse_args()

    if args.watch:
        return run_session_watch(project_root=ROOT_DIR, poll_seconds=args.poll_seconds)
    return run_session_once(
        project_root=ROOT_DIR,
        poll_seconds=args.poll_seconds,
        max_wait_seconds=args.max_wait_seconds,
        wait_for_result_after_manual_submit=args.wait_for_result_entry or args.max_wait_seconds > 0,
    )


if __name__ == "__main__":
    raise SystemExit(main())
