from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.concept_to_composition.concept_midi_generator import generate_concept_candidates  # noqa: E402
from features.concept_to_composition.concept_schema import SongConceptBrief  # noqa: E402


def main() -> int:
    concept_dir = ROOT_DIR / "concepts" / "song_idea_001"
    brief_path = concept_dir / "song_concept_brief.json"
    output_root = ROOT_DIR / "outputs" / "concept_song_idea_001"

    brief_payload = json.loads(brief_path.read_text(encoding="utf-8"))
    brief = SongConceptBrief.model_validate(brief_payload)
    candidates = generate_concept_candidates(brief, output_root)

    for candidate in candidates:
        print(f"CANDIDATE={candidate.name}")
        print(f"FULL_MIDI={candidate.full_midi_path.as_posix()}")
        for role, path in candidate.stem_paths.items():
            print(f"STEM_{role.upper()}={path.as_posix()}")
        print(f"GENERATION_REPORT_MD={candidate.generation_report_path.as_posix()}")
        print(f"ALIGNMENT_REPORT_MD={candidate.concept_alignment_report_path.as_posix()}")
        print(f"PROVENANCE_REPORT_MD={candidate.provenance_report_path.as_posix()}")
        print(f"REVIEW_SHEET={candidate.review_sheet_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
