from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT_DIR / "reports" / "model_integrations"
SYMBOLIC_BACKENDS = ("text2midi", "moonbeam", "midigpt", "musicbert")


def build_install_plan() -> dict[str, Any]:
    plan_rows = [
        {
            "backend_id": backend_id,
            "manual_steps": [
                "Clone repository manually into a local-only model repository folder (do not commit repo).",
                "Place model/tokenizer weights manually in local-only weight/cache folders (do not commit weights).",
                "Set config/model_integrations/model_integrations.local.json values.",
                f"Run scripts/dev.cmd run-{backend_id}-smoke-test for real local probe.",
            ],
            "automatic_execution_performed": False,
            "cloud_required": False,
            "modal_required": False,
        }
        for backend_id in SYMBOLIC_BACKENDS
    ]
    return {
        "status": "ok",
        "automatic_clone_performed": False,
        "automatic_download_performed": False,
        "automatic_install_performed": False,
        "cloud_called": False,
        "modal_called": False,
        "model_training_has_occurred": False,
        "backends": plan_rows,
        "notes": [
            "This planner is documentation only and performs no installs.",
            "All model setup is manual and local by default.",
        ],
    }


def write_plan(output_dir: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "symbolic_backend_install_plan.json"
    md_path = output_dir / "symbolic_backend_install_plan.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Symbolic Backend Install Plan",
        "",
        "- automatic_clone_performed: `False`",
        "- automatic_download_performed: `False`",
        "- automatic_install_performed: `False`",
        "- cloud_called: `False`",
        "- modal_called: `False`",
        "- model_training_has_occurred: `False`",
        "",
        "## Manual Steps",
    ]
    for row in payload["backends"]:
        lines.append(f"- `{row['backend_id']}`")
        for step in row["manual_steps"]:
            lines.append(f"  - {step}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Write manual symbolic backend install plan only.")
    parser.add_argument("--output-dir", default=REPORT_DIR.as_posix())
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    payload = build_install_plan()
    json_path, md_path = write_plan(output_dir, payload)
    print(f"SYMBOLIC_BACKEND_INSTALL_PLAN_JSON={json_path.as_posix()}")
    print(f"SYMBOLIC_BACKEND_INSTALL_PLAN_MD={md_path.as_posix()}")
    print("AUTOMATIC_INSTALL_PERFORMED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
