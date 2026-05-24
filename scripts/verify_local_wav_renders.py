from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.local_rendering.wav_verifier import write_verification_reports, verify_wav_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify local WAV render outputs.")
    parser.add_argument(
        "--generation-id",
        default="generated_wav_v1",
        help="Generation id to verify under renders/<generation_id>",
    )
    args = parser.parse_args()

    render_root = ROOT_DIR / "renders" / args.generation_id
    final_wav = render_root / "final.wav"
    stem_wavs = sorted((render_root / "stems").glob("*.wav")) if (render_root / "stems").exists() else []
    all_paths = [final_wav] + stem_wavs
    relative_paths = [path.relative_to(ROOT_DIR) if path.is_absolute() else path for path in all_paths]
    results = [
        verify_wav_file(path, render_backend="local_rendering", source_midi_provenance="outputs/generated_wav_v1/full.mid")
        for path in relative_paths
    ]

    json_path = ROOT_DIR / "reports" / "local_rendering" / "wav_render_verification_report.json"
    md_path = ROOT_DIR / "reports" / "local_rendering" / "wav_render_verification_report.md"
    write_verification_reports(results, json_path=json_path, md_path=md_path)

    rendered = any(item.exists and item.readable and item.duration_seconds > 0 and item.nonzero_samples for item in results)
    print(f"WAV_VERIFICATION_REPORT_JSON={json_path.as_posix()}")
    print(f"WAV_VERIFICATION_REPORT_MD={md_path.as_posix()}")
    print(f"WAV_RENDERED={str(rendered).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
