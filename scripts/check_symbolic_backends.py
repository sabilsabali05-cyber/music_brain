from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.symbolic_model_ensemble.capability_registry import backend_availability_payload
from features.symbolic_model_ensemble.ensemble_orchestrator import SymbolicEnsembleOrchestrator


def check_symbolic_backends(output_dir: Path) -> tuple[Path, Path, Path, Path, dict]:
    payload = backend_availability_payload()
    by_id = {row["backend_id"]: row for row in payload.get("backends", [])}
    for backend in ["moonbeam", "musicbert", "midigpt", "text2midi", "example_retrieval"]:
        if backend not in by_id:
            by_id[backend] = {
                "backend_id": backend,
                "status": "unavailable",
                "reason": "backend_not_registered",
                "backend_role": "unknown",
                "supported_operations": [],
                "limitations": [],
            }
    payload["backends"] = [by_id[name] for name in ["moonbeam", "musicbert", "midigpt", "text2midi", "example_retrieval"]]

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "backend_availability_report.json"
    md_path = output_dir / "backend_availability_report.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Symbolic Backend Availability Report",
        "",
    ]
    for row in payload["backends"]:
        lines.append(f"- `{row['backend_id']}`: `{row['status']}` reason=`{row['reason']}`")
    lines.extend(["", "## Limitations"])
    lines.extend([f"- {item}" for item in payload.get("limitations", [])])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    orchestrator = SymbolicEnsembleOrchestrator()
    routing_json, routing_md, _ = orchestrator.write_routing_report(output_dir)
    return json_path, md_path, routing_json, routing_md, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Check symbolic ensemble backend availability.")
    parser.add_argument("--output-dir", default="reports/symbolic_backends")
    args = parser.parse_args()
    json_path, md_path, routing_json, routing_md, _ = check_symbolic_backends(ROOT_DIR / args.output_dir)
    print(f"SYMBOLIC_BACKEND_AVAILABILITY_JSON={json_path.as_posix()}")
    print(f"SYMBOLIC_BACKEND_AVAILABILITY_MD={md_path.as_posix()}")
    print(f"SYMBOLIC_ROUTING_PLAN_JSON={routing_json.as_posix()}")
    print(f"SYMBOLIC_ROUTING_PLAN_MD={routing_md.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
