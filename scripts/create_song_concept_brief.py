from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.concept_to_composition.conversation_parser import (  # noqa: E402
    extract_conversation_markdown_text,
    parse_conversation_to_brief,
)


def main() -> int:
    concept_dir = ROOT_DIR / "concepts" / "song_idea_001"
    conversation_path = concept_dir / "conversation.md"
    brief_json_path = concept_dir / "song_concept_brief.json"
    brief_md_path = concept_dir / "song_concept_brief.md"

    conversation_text = conversation_path.read_text(encoding="utf-8")
    brief = parse_conversation_to_brief(extract_conversation_markdown_text(conversation_text))

    concept_dir.mkdir(parents=True, exist_ok=True)
    brief_json_path.write_text(json.dumps(brief.model_dump(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    brief_md_path.write_text(brief.to_markdown(), encoding="utf-8")

    print(f"SONG_CONCEPT_BRIEF_JSON={brief_json_path.as_posix()}")
    print(f"SONG_CONCEPT_BRIEF_MD={brief_md_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
