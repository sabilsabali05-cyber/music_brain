from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.local_rendering.ableton_backend import create_ableton_assisted_render_pack  # noqa: E402
from features.local_rendering.midi_to_render_plan import build_render_plan_from_stems  # noqa: E402
from features.local_rendering.vst_registry_schema import load_registry  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an honest Ableton assisted local render pack.")
    parser.add_argument("generation_id", help="Generation id")
    parser.add_argument("--reason", default="automation_unavailable", help="Reason for assisted pack fallback")
    parser.add_argument("--stems-dir", default="", help="Optional stems directory override")
    args = parser.parse_args()

    generation_id = args.generation_id
    stems_dir = Path(args.stems_dir) if args.stems_dir else (ROOT_DIR / "outputs" / generation_id / "stems")
    registry = load_registry(ROOT_DIR / "config" / "local_vst_registry.local.json")
    plan = build_render_plan_from_stems(
        generation_id=generation_id,
        stems_dir=stems_dir,
        registry=registry,
        default_backend="ableton_assisted_render",
    )
    report = create_ableton_assisted_render_pack(
        generation_id=generation_id,
        stems_dir=stems_dir,
        plan=plan,
        reason=args.reason,
    )
    print(f"ABLETON_ASSISTED_PACK={report.pack_path}")
    print("WAV_RENDERED=false")
    print("RENDER_PLAN_ONLY=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
