from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
PUBLIC_JSON = ROOT_DIR / "reports" / "synplant" / "synplant_session_plan.public.json"
PUBLIC_MD = ROOT_DIR / "reports" / "synplant" / "synplant_session_plan.public.md"
PRIVATE_JSON = ROOT_DIR / "reports" / "synplant" / "private_synplant_session_paths.json"
PRIVATE_MD = ROOT_DIR / "reports" / "synplant" / "private_synplant_session_paths.md"
TEXTURE_PLAN_JSON = ROOT_DIR / "reports" / "texture_intelligence" / "texture_analysis_plan.json"


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


def _load_sample_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted((ROOT_DIR / "datasets" / "sample_libraries").glob("**/sample_seed_records.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    records.append(payload)
    return records


def _source_policy(record: dict[str, Any]) -> str:
    source_type = str(record.get("source_type", "")).lower()
    authorization = str(record.get("authorization_status", "")).lower()
    intended_uses = [str(item).lower() for item in record.get("intended_uses", []) if isinstance(item, str)]
    if "splice" in source_type:
        return "splice_production_only"
    if source_type.startswith("local_sample_seed") and authorization in {"trusted_for_training", "approved_for_training"}:
        if any("training" in item for item in intended_uses):
            return "user_owned_training_candidate"
    if source_type.startswith("local_sample_seed"):
        return "production_only_training_excluded"
    return "unknown_blocked"


def _score_for_role(track_role: str, record: dict[str, Any], texture_map: dict[str, list[str]]) -> float:
    role = track_role.lower()
    asset_type = str(record.get("asset_type_guess", "unknown"))
    filename = str(record.get("filename", "")).lower()
    role_candidates = [str(item.get("role", "")).lower() for item in record.get("role_candidates", []) if isinstance(item, dict)]
    analysis_needs = texture_map.get(str(record.get("sample_id", "")), [])

    score = 0.1
    if role in role_candidates:
        score += 0.5
    if role == "drums" and asset_type in {"drum_break", "drum_loop", "drum_one_shot", "percussion_loop"}:
        score += 0.35
    if role == "bass" and asset_type in {"bass_one_shot", "synth_one_shot"}:
        score += 0.35
    if role in {"lead", "chords"} and asset_type in {"synth_one_shot", "chord_stab", "vocal_chop"}:
        score += 0.32
    if role == "texture_bed" and asset_type in {"texture", "drone", "field_recording"}:
        score += 0.35
    if role == "transition_fx" and asset_type in {"fx", "riser", "texture"}:
        score += 0.35
    if role.replace("_", " ") in filename or role in filename:
        score += 0.1
    if "synplant_seed_fit_analysis" in analysis_needs:
        score += 0.05
    return min(1.0, score)


def create_synplant_session_plan(ableton_project_folder: Path) -> tuple[Path, Path, Path, Path, dict[str, Any]]:
    track_setup = _read_json(ableton_project_folder / "track_setup.json")
    tracks = [item for item in track_setup.get("tracks", []) if isinstance(item, dict)]
    sample_records = _load_sample_records()
    texture_plan = _read_json(TEXTURE_PLAN_JSON)
    texture_map: dict[str, list[str]] = {}
    for item in texture_plan.get("analysis_plan", []):
        if isinstance(item, dict):
            texture_map[str(item.get("sample_id", ""))] = [str(v) for v in item.get("analysis_needed", [])]

    public_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []

    for track in tracks:
        role = str(track.get("role", "unknown"))
        ranked = sorted(
            sample_records,
            key=lambda row: _score_for_role(role, row, texture_map),
            reverse=True,
        )
        selected = ranked[:5]
        if len(selected) < 3:
            selected = ranked[:3]
        for row in selected:
            policy = _source_policy(row)
            sample_id = str(row.get("sample_id", "unknown"))
            public_rows.append(
                {
                    "track_role": role,
                    "seed_sample_id": sample_id,
                    "public_safe_sample_label": f"{sample_id} ({row.get('asset_type_guess', 'unknown')})",
                    "source_policy": policy,
                    "fit_score": round(_score_for_role(role, row, texture_map), 3),
                    "generation_method": "manual",
                    "automation_claimed": False,
                    "seed_notes": [
                        "Manual Synplant session candidate only.",
                        "No Synplant automation claim.",
                    ],
                }
            )
            private_rows.append(
                {
                    "track_role": role,
                    "seed_sample_id": sample_id,
                    "local_source_path_private": str(row.get("source_path", "")),
                    "source_policy": policy,
                }
            )

    payload = {
        "status": "ok",
        "created_at": now_iso(),
        "ableton_project_folder": ableton_project_folder.resolve().relative_to(ROOT_DIR.resolve()).as_posix(),
        "generation_method": "manual",
        "automation_claimed": False,
        "seed_candidates": public_rows,
        "limitations": [
            "No Synplant automation claim.",
            "Public report excludes private local paths.",
            "Derived patches must inherit source restrictions from selected seed.",
        ],
    }

    PUBLIC_JSON.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    PRIVATE_JSON.write_text(
        json.dumps(
            {
                "status": "private_local_only",
                "created_at": now_iso(),
                "entries": private_rows,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Synplant Session Plan (Public)",
        "",
        f"- status: `{payload['status']}`",
        "- generation_method: `manual`",
        "- automation_claimed: `False`",
        f"- seed_candidates: `{len(public_rows)}`",
        "",
        "## Proposed Seeds",
    ]
    if public_rows:
        for row in public_rows:
            lines.append(
                f"- role `{row['track_role']}` -> `{row['seed_sample_id']}` [{row['source_policy']}] score={row['fit_score']}"
            )
    else:
        lines.append("- none (sample library records missing)")
    lines.extend(["", "## Limitations"])
    lines.extend([f"- {item}" for item in payload["limitations"]])
    lines.append("")
    PUBLIC_MD.write_text("\n".join(lines), encoding="utf-8")

    PRIVATE_MD.write_text(
        "\n".join(
            [
                "# Synplant Session Paths (Private)",
                "",
                "Private local source path references for manual session execution.",
                "This file is local-only and ignored by git.",
                "",
                f"- entries: `{len(private_rows)}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return PUBLIC_JSON, PUBLIC_MD, PRIVATE_JSON, PRIVATE_MD, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Synplant session seed plan from Ableton export + sample index.")
    parser.add_argument("ableton_project_folder", help="Path to Ableton project export root")
    args = parser.parse_args()
    public_json, public_md, private_json, private_md, payload = create_synplant_session_plan(Path(args.ableton_project_folder))
    print(f"SYNPLANT_SESSION_PLAN_PUBLIC_JSON={public_json.as_posix()}")
    print(f"SYNPLANT_SESSION_PLAN_PUBLIC_MD={public_md.as_posix()}")
    print(f"SYNPLANT_SESSION_PLAN_PRIVATE_JSON={private_json.as_posix()}")
    print(f"SYNPLANT_SESSION_PLAN_PRIVATE_MD={private_md.as_posix()}")
    print(f"SYNPLANT_SEED_CANDIDATE_COUNT={len(payload['seed_candidates'])}")
    print("SYNPLANT_AUTOMATION_CLAIMED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
