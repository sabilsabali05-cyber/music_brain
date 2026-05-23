from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.symbolic_models.backends.registry import check_symbolic_model_backends


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _task_needs_multitrack(task: str) -> bool:
    return task in {"call_response", "section_transition", "buildup_to_release"}


def _recommended_order(task: str, prompt: str | None) -> list[str]:
    order = ["example_retrieval"]
    if task in {"continuation", "phrase_continuation", "harmony_continuation", "melody_continuation", "groove_continuation", "infill_missing_region"}:
        order.append("moonbeam")
    if _task_needs_multitrack(task):
        order.append("midigpt")
    if task == "text_to_midi" or (prompt and prompt.strip()):
        order.append("text2midi")
    order.append("musicbert")
    dedup: list[str] = []
    for item in order:
        if item not in dedup:
            dedup.append(item)
    return dedup


def plan_symbolic_generation(
    dataset_folder: Path,
    *,
    task: str,
    prompt: str | None = None,
) -> tuple[Path, Path]:
    dataset_folder = dataset_folder.resolve()
    manifest = _read_json(dataset_folder / "generative_manifest.json")
    examples = _read_jsonl(dataset_folder / "generative_examples.jsonl")
    availability = check_symbolic_model_backends()
    availability_by_id = {item.provider_id: item for item in availability}

    task_examples = [row for row in examples if str(row.get("task_type", "")) == task]
    fallback_chain = _recommended_order(task, prompt)
    provider_plan: list[dict[str, Any]] = []
    for provider_id in fallback_chain:
        if provider_id == "example_retrieval":
            provider_plan.append(
                {
                    "provider_id": "example_retrieval",
                    "available": True,
                    "reason": "Existing generator from curated examples.",
                    "generation_allowed": True,
                }
            )
            continue
        availability_payload = availability_by_id.get(provider_id)
        provider_plan.append(
            {
                "provider_id": provider_id,
                "available": bool(availability_payload.available) if availability_payload else False,
                "role_hint": availability_payload.role_hint if availability_payload else "unknown",
                "installation_hint": availability_payload.installation_hint if availability_payload else "",
                "limitations": availability_payload.limitations if availability_payload else ["provider not registered"],
                "generation_allowed": bool(availability_payload.available) if availability_payload else False,
            }
        )

    plan = {
        "status": "planned",
        "dataset_folder": dataset_folder.as_posix(),
        "performance_id": str(manifest.get("performance_id") or dataset_folder.parent.name),
        "segment_run_id": str(manifest.get("segment_run_id") or dataset_folder.name),
        "requested_task": task,
        "prompt": prompt,
        "example_count_for_task": len(task_examples),
        "provider_fallback_order": fallback_chain,
        "provider_plan": provider_plan,
        "fallback_policy": [
            "existing example generator",
            "Moonbeam for continuation/infill tasks",
            "MIDI-GPT for multitrack/controllable tasks",
            "Text2MIDI for prompt-only sketch tasks",
            "MusicBERT for ranking/evaluation",
        ],
        "note": "Planning only. No symbolic model generation executed in this script.",
    }

    json_path = dataset_folder / "symbolic_generation_plan.json"
    md_path = dataset_folder / "symbolic_generation_plan.md"
    json_path.write_text(json.dumps(plan, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Symbolic Generation Plan",
        "",
        f"- dataset_folder: `{dataset_folder.as_posix()}`",
        f"- requested_task: `{task}`",
        f"- prompt: `{prompt or ''}`",
        f"- example_count_for_task: `{len(task_examples)}`",
        f"- provider_fallback_order: `{fallback_chain}`",
        "",
        "## Provider Plan",
    ]
    for item in provider_plan:
        lines.append(
            f"- `{item['provider_id']}` available=`{item['available']}` generation_allowed=`{item['generation_allowed']}` "
            f"limitations=`{item.get('limitations', [])}`"
        )
    lines.extend(
        [
            "",
            "## Fallback Policy",
            "- existing example generator",
            "- Moonbeam for continuation/infill",
            "- MIDI-GPT for multitrack/controls",
            "- Text2MIDI for prompt-only",
            "- MusicBERT for ranking/evaluation",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan symbolic backend usage for a generative dataset task.")
    parser.add_argument("generative_dataset_folder", help="Path to generative dataset folder")
    parser.add_argument("--task", default="continuation", help="Task type for planning")
    parser.add_argument("--prompt", default=None, help="Optional text prompt")
    args = parser.parse_args()
    json_path, md_path = plan_symbolic_generation(
        Path(args.generative_dataset_folder),
        task=args.task,
        prompt=args.prompt,
    )
    print(f"SYMBOLIC_GENERATION_PLAN_JSON={json_path.as_posix()}")
    print(f"SYMBOLIC_GENERATION_PLAN_MD={md_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
