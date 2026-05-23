from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT_DIR / "reports" / "texture_intelligence" / "sound_palette_context.json"
OUT_MD = ROOT_DIR / "reports" / "texture_intelligence" / "sound_palette_context.md"
SYNPLANT_PLAN = ROOT_DIR / "reports" / "synplant" / "synplant_session_plan.public.json"
TEXTURE_PLAN = ROOT_DIR / "reports" / "texture_intelligence" / "texture_analysis_plan.public.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _bucket_for_role(role: str) -> str:
    role = role.lower()
    if role in {"bass", "drums"}:
        return "low"
    if role in {"chords", "texture_bed"}:
        return "mid"
    if role in {"lead", "transition_fx"}:
        return "high"
    return "mid"


def build_sound_palette_context(ableton_project_folder: Path) -> tuple[Path, Path, dict[str, Any]]:
    track_setup = _read_json(ableton_project_folder / "track_setup.json")
    tracks = [item for item in track_setup.get("tracks", []) if isinstance(item, dict)]
    roles = [str(item.get("role", "unknown")) for item in tracks]
    synplant = _read_json(SYNPLANT_PLAN)
    texture = _read_json(TEXTURE_PLAN)

    foreground_roles = [role for role in roles if role in {"lead", "drums", "bass"}]
    background_roles = [role for role in roles if role in {"chords", "texture_bed", "transition_fx"}]

    low = [role for role in roles if _bucket_for_role(role) == "low"]
    mid = [role for role in roles if _bucket_for_role(role) == "mid"]
    high = [role for role in roles if _bucket_for_role(role) == "high"]

    density_by_section = {"intro": float(len(roles))}
    contrast_pairs = ["bass_vs_lead", "drums_vs_texture_bed", "chords_vs_transition_fx"]
    masking_risks: list[str] = []
    if "lead" in roles and "chords" in roles:
        masking_risks.append("lead/chords mid-high overlap risk")
    if "texture_bed" in roles and "transition_fx" in roles:
        masking_risks.append("texture_bed/transition_fx high-band buildup risk")

    expected_roles = {"drums", "bass", "chords", "lead", "texture_bed", "transition_fx"}
    missing_roles = sorted(expected_roles.difference(set(roles)))
    suggestions = [f"add_{item}" for item in missing_roles]

    payload = {
        "status": "ok",
        "created_at": now_iso(),
        "project_folder": ableton_project_folder.resolve().relative_to(ROOT_DIR.resolve()).as_posix(),
        "foreground_roles": foreground_roles,
        "background_roles": background_roles,
        "low_spectral_occupancy": low,
        "mid_spectral_occupancy": mid,
        "high_spectral_occupancy": high,
        "density_by_section": density_by_section,
        "contrast_pairs": contrast_pairs,
        "masking_risks": masking_risks,
        "missing_texture_roles": missing_roles,
        "suggested_additions": suggestions,
        "evidence_refs": [
            ableton_project_folder.resolve().relative_to(ROOT_DIR.resolve()).as_posix() + "/track_setup.json",
            "reports/synplant/synplant_session_plan.public.json" if synplant else "reports/synplant/synplant_session_plan.public.json (missing)",
            "reports/texture_intelligence/texture_analysis_plan.json" if texture else "reports/texture_intelligence/texture_analysis_plan.json (missing)",
        ],
        "limitations": [
            "Context uses track-role planning metadata only (no new audio processing).",
            "No Synplant automation claim.",
        ],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "\n".join(
            [
                "# Sound Palette Context",
                "",
                f"- status: `{payload['status']}`",
                f"- foreground_roles: `{', '.join(payload['foreground_roles']) or 'none'}`",
                f"- background_roles: `{', '.join(payload['background_roles']) or 'none'}`",
                f"- missing_texture_roles: `{', '.join(payload['missing_texture_roles']) or 'none'}`",
                "",
                "## Masking Risks",
                *([f"- {item}" for item in payload["masking_risks"]] or ["- none"]),
                "",
                "## Suggested Additions",
                *([f"- {item}" for item in payload["suggested_additions"]] or ["- none"]),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return OUT_JSON, OUT_MD, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build collective sound palette context from planning artifacts.")
    parser.add_argument("ableton_project_folder", help="Path to Ableton export project folder")
    args = parser.parse_args()
    out_json, out_md, payload = build_sound_palette_context(Path(args.ableton_project_folder))
    print(f"SOUND_PALETTE_CONTEXT_JSON={out_json.as_posix()}")
    print(f"SOUND_PALETTE_CONTEXT_MD={out_md.as_posix()}")
    print(f"MISSING_TEXTURE_ROLE_COUNT={len(payload['missing_texture_roles'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
