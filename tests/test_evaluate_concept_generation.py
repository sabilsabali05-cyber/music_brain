from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.evaluate_concept_generation import main as evaluate_main  # noqa: E402
from scripts.generate_midi_from_concept import main as generate_main  # noqa: E402
from scripts.create_song_concept_brief import main as brief_main  # noqa: E402


def test_evaluate_concept_generation_end_to_end() -> None:
    assert brief_main() == 0
    assert generate_main() == 0
    assert evaluate_main() == 0
    report = ROOT_DIR / "reports" / "concept_to_composition" / "song_idea_001_eval.json"
    assert report.exists()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["best_candidate"].startswith("candidate_")
    assert len(payload["candidates"]) == 3
    for candidate in payload["candidates"]:
        assert "concept_alignment_score" in candidate
        assert "midi_parse_success" in candidate


def test_reports_do_not_include_private_paths_or_cloud_claims() -> None:
    report = ROOT_DIR / "reports" / "concept_to_composition" / "song_idea_001_eval.json"
    if not report.exists():
        return
    text = report.read_text(encoding="utf-8")
    assert "C:/Users/izzyo" not in text
    assert "C:\\Users\\izzyo" not in text
    assert "HF_TOKEN" not in text
    assert "MODAL_TOKEN" not in text
