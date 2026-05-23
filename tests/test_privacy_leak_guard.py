from __future__ import annotations

import json
from pathlib import Path

from scripts.check_privacy_leaks import scan_privacy_leaks


def test_privacy_scan_flags_new_public_absolute_path(tmp_path: Path) -> None:
    tracked = tmp_path / "reports" / "public_report.md"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text("Leaked path C:/Users/tester/Desktop/file.wav", encoding="utf-8")

    payload = scan_privacy_leaks(
        project_root=tmp_path,
        tracked_files=[tracked],
        changed_files={"reports/public_report.md"},
    )
    assert payload["status"] == "fail"
    assert payload["new_public_leak_count"] == 1
    assert payload["pre_existing_historical_path_debt_count"] == 0


def test_privacy_scan_reports_historical_debt_without_failure(tmp_path: Path) -> None:
    tracked = tmp_path / "datasets" / "old_dataset.json"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text(r"C:\Users\legacy\OneDrive\Desktop\sounds\old.wav", encoding="utf-8")

    payload = scan_privacy_leaks(
        project_root=tmp_path,
        tracked_files=[tracked],
        changed_files=set(),
    )
    assert payload["status"] == "ok"
    assert payload["new_public_leak_count"] == 0
    assert payload["pre_existing_historical_path_debt_count"] >= 1


def test_privacy_scan_allows_private_allowlisted_paths(tmp_path: Path) -> None:
    private = tmp_path / "outputs" / "ableton_project_v1" / "AI_Generated_Song_Project" / "private_synplant_seed_paths.json"
    private.parent.mkdir(parents=True, exist_ok=True)
    private.write_text(json.dumps({"source_path": "C:/Users/private/path.wav"}), encoding="utf-8")

    payload = scan_privacy_leaks(
        project_root=tmp_path,
        tracked_files=[private],
        changed_files={"outputs/ableton_project_v1/AI_Generated_Song_Project/private_synplant_seed_paths.json"},
    )
    assert payload["status"] == "ok"
    assert payload["new_public_leak_count"] == 0


def test_privacy_scan_enforces_public_outputs_even_if_not_changed(tmp_path: Path) -> None:
    tracked = (
        tmp_path
        / "outputs"
        / "generated_midi"
        / "fixture"
        / "generation_report.json"
    )
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text(
        '{"manifest_path":"' + "C:/" + "Users/izzyo/AppData/Local/Temp/example.json" + '"}',
        encoding="utf-8",
    )

    payload = scan_privacy_leaks(
        project_root=tmp_path,
        tracked_files=[tracked],
        changed_files=set(),
    )
    assert payload["status"] == "fail"
    assert payload["new_public_leak_count"] >= 1
    assert any(item["marker"] == "C:/Users/" for item in payload["new_public_leaks"])
