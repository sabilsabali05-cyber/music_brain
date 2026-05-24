from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.local_rendering.wav_verifier import verify_wav_file, write_verification_reports  # noqa: E402

GENERATION_ID = "chordpotion_generation_v1"


def _run(script_name: str) -> None:
    script = ROOT_DIR / "scripts" / script_name
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, cwd=ROOT_DIR, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{script_name} failed:\n{result.stdout}\n{result.stderr}")


def main() -> int:
    _run("generate_chordpotion_ready_skeleton.py")
    _run("build_chordpotion_transform_plan.py")
    _run("render_chordpotion_with_reaper.py")

    output_root = ROOT_DIR / "outputs" / GENERATION_ID
    output_root.mkdir(parents=True, exist_ok=True)
    render_result_path = output_root / "render_result.json"
    render_payload = json.loads(render_result_path.read_text(encoding="utf-8")) if render_result_path.exists() else {}

    wav_path = ROOT_DIR / "renders" / GENERATION_ID / "final.wav"
    wav_path_rel = Path("renders") / GENERATION_ID / "final.wav"
    source_midi_rel = Path("outputs") / GENERATION_ID / "harmony_skeleton.mid"
    wav_verification = verify_wav_file(
        wav_path_rel,
        render_backend="reaper_auto_render_chordpotion",
        source_midi_provenance=source_midi_rel.as_posix(),
    )
    wav_rendered = bool(
        wav_verification.exists
        and wav_verification.readable
        and wav_verification.duration_seconds > 0
        and wav_verification.nonzero_samples
    )

    if not wav_rendered:
        _run("export_chordpotion_ableton_pack.py")

    wav_status = "rendered_wav_available" if wav_rendered else "assisted_render_pack_created"
    (output_root / "wav_status.md").write_text(wav_status + "\n", encoding="utf-8")

    verification_json = ROOT_DIR / "reports" / "local_rendering" / f"{GENERATION_ID}_wav_verification.json"
    verification_md = ROOT_DIR / "reports" / "local_rendering" / f"{GENERATION_ID}_wav_verification.md"
    write_verification_reports([wav_verification], json_path=verification_json, md_path=verification_md)
    status_md = ROOT_DIR / "reports" / "local_rendering" / f"{GENERATION_ID}_wav_status.md"
    status_md.write_text(
        "\n".join(
            [
                "# ChordPotion WAV Status",
                "",
                f"- wav_rendered: `{str(wav_rendered).lower()}`",
                f"- final_wav_path: `{wav_path_rel.as_posix() if wav_rendered else 'none'}`",
                f"- status: `{wav_status}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    final_payload = dict(render_payload)
    final_payload["wav_rendered"] = wav_rendered
    final_payload["final_wav_path"] = wav_path_rel.as_posix() if wav_rendered else ""
    final_payload["wav_status"] = wav_status
    (output_root / "render_result.json").write_text(json.dumps(final_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(f"WAV_RENDERED={str(wav_rendered).lower()}")
    print(f"FINAL_WAV_PATH={final_payload['final_wav_path'] or 'none'}")
    print(f"WAV_STATUS={wav_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

