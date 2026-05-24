from __future__ import annotations

import json
from pathlib import Path


def test_generated_artifact_policy_and_privacy_debt_report_exist() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    policy_path = repo_root / "docs" / "GENERATED_ARTIFACT_POLICY.md"
    debt_json_path = repo_root / "reports" / "integration" / "privacy_debt_report.json"
    debt_md_path = repo_root / "reports" / "integration" / "privacy_debt_report.md"

    assert policy_path.exists()
    assert debt_json_path.exists()
    assert debt_md_path.exists()

    policy_text = policy_path.read_text(encoding="utf-8")
    assert "Must Not Commit" in policy_text
    assert "Rendered WAV outputs unless explicitly approved" in policy_text
    assert "do not silently delete user outputs" in policy_text.lower()

    debt_payload = json.loads(debt_json_path.read_text(encoding="utf-8"))
    assert debt_payload["silent_ignore_allowed"] is False
    assert debt_payload["privacy_scan_status"] in {"ok", "fail"}
    assert isinstance(debt_payload["recommended_actions"], list) and debt_payload["recommended_actions"]
