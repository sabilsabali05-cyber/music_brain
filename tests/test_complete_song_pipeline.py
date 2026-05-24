from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_complete_song_pipeline_writes_honest_status_and_artifacts() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "generate_complete_song_wav.py"
    result = subprocess.run([sys.executable, str(script)], cwd=repo_root, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr

    output_root = repo_root / "outputs" / "complete_song_v1"
    status_json_path = repo_root / "reports" / "integration" / "complete_song_pipeline_status.json"
    feedback_path = repo_root / "reports" / "review_queue" / "complete_song_v1_feedback_template.json"
    wav_status_path = output_root / "wav_status.md"
    review_sheet = output_root / "review_sheet.md"

    assert status_json_path.exists()
    assert feedback_path.exists()
    assert wav_status_path.exists()
    assert review_sheet.exists()

    payload = json.loads(status_json_path.read_text(encoding="utf-8"))
    wav_status = wav_status_path.read_text(encoding="utf-8").strip()
    assert payload["local_mode_only"] is True
    assert payload["cloud_called"] is False
    assert payload["chordpotion"]["status"] in {"missing_config", "attempted", "attempted_no_transform_capture"}
    assert payload["render"]["reaper_status"] in {"available", "missing_config"}
    assert payload["render"]["vst_status"] in {"configured", "missing_config"}
    assert payload["selector"]["selector_status"] in {"trained_selector_used", "heuristic_or_unconfirmed"}
    assert payload["training"]["training_status"] in {
        "not_allowed_no_explicit_labels",
        "trained_selector_available",
        "labels_present_trained_selector_unconfirmed",
    }
    if payload["render"]["wav_rendered"]:
        assert wav_status == "rendered_wav_available"
        assert payload["render"]["final_wav_path"]
    else:
        assert wav_status == "assisted_render_pack_created"
        assert payload["blockers"]
        assert payload["fallback_paths"]["direct_stems_render_fallback_used"] is True
