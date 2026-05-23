from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.texture_sound.synplant_session_log_schema import SynplantSessionLog, validate_synplant_session_log  # noqa: E402


def append_synplant_session(payload: dict[str, object]) -> Path:
    valid, errors = validate_synplant_session_log(payload)
    if not valid:
        raise ValueError("; ".join(errors))
    row = SynplantSessionLog(
        session_id=str(payload["session_id"]),
        patch_name=str(payload["patch_name"]),
        seed_strategy=str(payload.get("seed_strategy", "manual")),
        rating=int(payload["rating"]),
        notes=str(payload.get("notes", "")),
        training_allowed=bool(payload.get("training_allowed", False)),
    ).as_dict()
    output_path = ROOT_DIR / "datasets" / "synplant" / "session_logs_v1.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Append a validated Synplant session log row.")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--patch-name", required=True)
    parser.add_argument("--seed-strategy", default="manual")
    parser.add_argument("--rating", type=int, required=True)
    parser.add_argument("--notes", default="")
    parser.add_argument("--training-allowed", action="store_true")
    args = parser.parse_args()
    output = append_synplant_session(
        {
            "session_id": args.session_id,
            "patch_name": args.patch_name,
            "seed_strategy": args.seed_strategy,
            "rating": args.rating,
            "notes": args.notes,
            "training_allowed": args.training_allowed,
        }
    )
    print(f"SYNPLANT_SESSION_LOG_PATH={output.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
