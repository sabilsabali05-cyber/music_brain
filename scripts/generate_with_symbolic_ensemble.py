from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.symbolic_model_ensemble.ensemble_orchestrator import SymbolicEnsembleOrchestrator


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate symbolic candidate via model ensemble orchestrator.")
    parser.add_argument("prompt", help="Text prompt for symbolic generation.")
    parser.add_argument(
        "--output-dir",
        default="outputs/symbolic_ensemble_v1",
        help="Output folder for ensemble artifacts.",
    )
    args = parser.parse_args()
    orchestrator = SymbolicEnsembleOrchestrator()
    report = orchestrator.generate(args.prompt, output_root=(ROOT_DIR / args.output_dir))
    print(f"SYMBOLIC_ENSEMBLE_REPORT_JSON={(ROOT_DIR / args.output_dir / 'ensemble_generation_report.json').as_posix()}")
    print(f"SYMBOLIC_ENSEMBLE_REPORT_MD={(ROOT_DIR / args.output_dir / 'ensemble_generation_report.md').as_posix()}")
    print(f"SYMBOLIC_ENSEMBLE_SELECTED_MIDI={report.get('selected_candidate_midi', '')}")
    print(f"SYMBOLIC_ENSEMBLE_FALLBACK_USED={report.get('example_retrieval_fallback', False)}")
    print(f"SYMBOLIC_ENSEMBLE_NO_REAL_BACKEND={report.get('no_real_symbolic_backend_available', False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
