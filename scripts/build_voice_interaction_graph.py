from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.music_cognition.voice_interaction_builder import build_voice_interaction_graph
from scripts.cloud_full_activation_common import MUSIC_COGNITION_REPORTS_DIR, now_iso
from features.cloud_execution.cloud_artifact_policy import redact_public_payload, redact_public_text


def build_graph_payload() -> dict[str, object]:
    graph = build_voice_interaction_graph(graph_id="voice_interaction_graph_v1", stems=[], events=[], witnesses=[])
    payload = graph.as_dict()
    payload["created_at"] = now_iso()
    payload["output_files"] = [
        "reports/music_cognition/voice_interaction_graph.json",
        "reports/music_cognition/voice_interaction_graph.md",
    ]
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build voice interaction graph scaffold from available evidence.")
    parser.add_argument("--output-dir", default=MUSIC_COGNITION_REPORTS_DIR.as_posix())
    args = parser.parse_args()
    payload = build_graph_payload()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    json_path = output_dir / "voice_interaction_graph.json"
    md_path = output_dir / "voice_interaction_graph.md"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(redact_public_payload(payload), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Voice Interaction Graph",
        "",
        f"- status: `{payload['status']}`",
        f"- graph_generated: `{payload['graph_generated']}`",
        "- output_files: `reports/music_cognition/voice_interaction_graph.json`, `reports/music_cognition/voice_interaction_graph.md`",
    ]
    md_path.write_text(redact_public_text("\n".join(lines) + "\n"), encoding="utf-8")
    print(f"VOICE_INTERACTION_GRAPH_JSON={json_path.as_posix()}")
    print(f"VOICE_INTERACTION_GRAPH_MD={md_path.as_posix()}")
    print(f"VOICE_GRAPH_STATUS={payload['status']}")
    print(f"VOICE_GRAPH_GENERATED={payload['graph_generated']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
