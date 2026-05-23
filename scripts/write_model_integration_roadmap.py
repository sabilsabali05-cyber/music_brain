from __future__ import annotations

import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

ROADMAP_STEPS = [
    "Fix privacy gate and redact public leak surfaces.",
    "Re-run privacy scanner and direct grep leak gates.",
    "Register all model families and default-unavailable integration metadata.",
    "Ship local config template with every model disabled by default.",
    "Run safe availability checker with no heavyweight imports by default.",
    "Generate availability report for configured vs available model state.",
    "Apply model policy hooks for authorization, reporting, and training safety.",
    "Validate transcription outputs as witness_not_truth in downstream decisions.",
    "Treat audio generation backends as reference_only unless explicitly enabled.",
    "Use source separation outputs as weak evidence pending human review.",
    "Train personalized rankers and preference models from authorized user feedback.",
    "Only then evaluate generator fine-tuning with validated training corpus.",
]


def write_model_integration_roadmap(output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Model Integration Roadmap",
        "",
        "Ordered implementation path from privacy gate to rankers-first personalization before generator fine-tuning:",
        "",
    ]
    for idx, step in enumerate(ROADMAP_STEPS, start=1):
        lines.append(f"{idx}. {step}")
    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Write model integration roadmap report.")
    parser.add_argument("--output", default="reports/model_integrations/model_integration_roadmap.md")
    args = parser.parse_args()
    output_path = write_model_integration_roadmap(ROOT_DIR / args.output)
    print(f"MODEL_INTEGRATION_ROADMAP_MD={output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
