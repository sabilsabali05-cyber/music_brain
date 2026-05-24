from __future__ import annotations

import json
from pathlib import Path

from mido import MidiFile

from features.concept_to_composition.concept_midi_generator import generate_concept_candidates
from features.concept_to_composition.conversation_parser import parse_conversation_to_brief


def test_generate_midi_candidates_and_reports(tmp_path: Path) -> None:
    brief = parse_conversation_to_brief("hopeful dark sparse pocket weird but musical")
    results = generate_concept_candidates(brief, tmp_path / "outputs")
    assert len(results) == 3
    for result in results:
        assert result.full_midi_path.exists()
        MidiFile(result.full_midi_path.as_posix())
        for path in result.stem_paths.values():
            assert path.exists()
            MidiFile(path.as_posix())
        report_json = result.generation_report_path.with_suffix(".json")
        payload = json.loads(report_json.read_text(encoding="utf-8"))
        assert payload["concept_brief_used"]["title"]
        assert payload["trained_model_generation_happened"] is False
        assert payload["real_symbolic_backend_used"] is False
        assert payload["fallback_rules_used"] is True
