from __future__ import annotations

import importlib.util
import json
import math
import os
import subprocess
import sys
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mido import MidiFile

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT_DIR / "reports" / "model_integration"
LOCAL_OUTPUTS = ROOT_DIR / "local_model_outputs"
LOCAL_ENVS = ROOT_DIR / ".local_model_envs"
LOCAL_REGISTRY = ROOT_DIR / "local_model_integration" / "active_model_registry.local.json"

MODEL_ORDER = ["basicpitch", "demucs", "mt3", "omnizart", "moonbeam", "musicbert", "midigpt", "text2midi"]
SYMBOLIC_MODELS = ["moonbeam", "musicbert", "midigpt", "text2midi"]
ENV_ROOTS = ["basicpitch", "demucs", "mt3", "omnizart", "moonbeam", "musicbert", "midigpt", "text2midi"]


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _redact_text(value: str) -> str:
    text = value.replace("\\", "/")
    text = text.replace(str(ROOT_DIR).replace("\\", "/"), "<REPO_ROOT>")
    text = text.replace(str(Path.home()).replace("\\", "/"), "<LOCAL_HOME>")
    text = text.replace("C:/Users/", "<LOCAL_HOME>/")
    return text


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _ensure_local_roots() -> None:
    for name in ENV_ROOTS:
        (LOCAL_ENVS / name).mkdir(parents=True, exist_ok=True)
    (LOCAL_OUTPUTS / "basicpitch").mkdir(parents=True, exist_ok=True)
    (LOCAL_OUTPUTS / "demucs").mkdir(parents=True, exist_ok=True)
    (ROOT_DIR / "local_model_weights").mkdir(parents=True, exist_ok=True)
    (ROOT_DIR / "local_model_cache").mkdir(parents=True, exist_ok=True)
    (ROOT_DIR / "local_model_integration").mkdir(parents=True, exist_ok=True)


def _build_source_loop(path: Path) -> dict[str, Any]:
    sample_rate = 22050
    duration_seconds = 2.0
    frequency = 440.0
    frame_count = int(sample_rate * duration_seconds)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for idx in range(frame_count):
            sample = int(12000 * math.sin(2 * math.pi * frequency * idx / sample_rate))
            wav.writeframesraw(sample.to_bytes(2, byteorder="little", signed=True))
    return {
        "path": path.relative_to(ROOT_DIR).as_posix(),
        "sample_rate": sample_rate,
        "duration_seconds": duration_seconds,
        "generation": "local_sine_wave",
    }


def _count_midi_notes(midi_path: Path) -> int:
    parsed = MidiFile(str(midi_path))
    count = 0
    for track in parsed.tracks:
        for msg in track:
            if msg.type == "note_on" and int(getattr(msg, "velocity", 0)) > 0:
                count += 1
    return count


def _run_basicpitch_smoke(source_loop: Path) -> dict[str, Any]:
    output_dir = LOCAL_OUTPUTS / "basicpitch"
    output_dir.mkdir(parents=True, exist_ok=True)
    midi_path = output_dir / "source_loop_basicpitch.mid"
    if not _module_available("basic_pitch"):
        return {
            "model": "basicpitch",
            "active": False,
            "status": "unavailable",
            "reason": "python_module_missing_basic_pitch",
            "note_count": 0,
            "smoke_output_midi": "",
            "smoke_output_audio": source_loop.relative_to(ROOT_DIR).as_posix(),
            "real_backend_observation": 0,
            "cloud_called": False,
        }
    try:
        from basic_pitch.inference import predict

        _, midi_data, note_events = predict(str(source_loop))
        midi_data.write(str(midi_path))
        note_count = _count_midi_notes(midi_path)
        active = note_count > 0
        return {
            "model": "basicpitch",
            "active": active,
            "status": "active" if active else "failed",
            "reason": "" if active else "note_count_zero",
            "note_count": int(note_count),
            "raw_note_events": int(len(note_events) if isinstance(note_events, list) else 0),
            "smoke_output_midi": midi_path.relative_to(ROOT_DIR).as_posix(),
            "smoke_output_audio": source_loop.relative_to(ROOT_DIR).as_posix(),
            "real_backend_observation": 1 if active else 0,
            "cloud_called": False,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "model": "basicpitch",
            "active": False,
            "status": "failed",
            "reason": f"{exc.__class__.__name__}:{exc}",
            "note_count": 0,
            "smoke_output_midi": "",
            "smoke_output_audio": source_loop.relative_to(ROOT_DIR).as_posix(),
            "real_backend_observation": 0,
            "cloud_called": False,
        }


def _demucs_local_checkpoint_exists() -> tuple[bool, list[str]]:
    candidates = [
        Path.home() / ".cache" / "torch" / "hub" / "checkpoints",
        ROOT_DIR / "local_model_weights",
    ]
    hits: list[str] = []
    for root in candidates:
        if not root.exists():
            continue
        for child in root.iterdir():
            name = child.name.lower()
            if "demucs" in name and child.is_file():
                hits.append(_redact_text(child.as_posix()))
    return bool(hits), hits


def _first_stem_dir(root: Path) -> Path | None:
    if not root.exists():
        return None
    for model_dir in sorted(root.iterdir()):
        if not model_dir.is_dir():
            continue
        for track_dir in sorted(model_dir.iterdir()):
            if track_dir.is_dir():
                return track_dir
    return None


def _readable_stems(stem_dir: Path | None) -> list[str]:
    if stem_dir is None:
        return []
    stems: list[str] = []
    for wav in sorted(stem_dir.glob("*.wav")):
        if wav.stat().st_size > 128:
            stems.append(wav.as_posix())
    return stems


def _run_demucs_smoke(source_loop: Path) -> dict[str, Any]:
    output_root = LOCAL_OUTPUTS / "demucs"
    output_root.mkdir(parents=True, exist_ok=True)
    if not _module_available("demucs"):
        return {
            "model": "demucs",
            "active": False,
            "status": "unavailable",
            "reason": "python_module_missing_demucs",
            "readable_stems": [],
            "smoke_output_root": output_root.relative_to(ROOT_DIR).as_posix(),
            "real_backend_observation": 0,
            "cloud_called": False,
        }

    has_checkpoint, checkpoint_hits = _demucs_local_checkpoint_exists()
    if not has_checkpoint:
        return {
            "model": "demucs",
            "active": False,
            "status": "blocked",
            "reason": "missing_local_demucs_checkpoint_offline_required",
            "checkpoint_hits": checkpoint_hits,
            "readable_stems": [],
            "smoke_output_root": output_root.relative_to(ROOT_DIR).as_posix(),
            "real_backend_observation": 0,
            "cloud_called": False,
        }

    cmd = [
        sys.executable,
        "-m",
        "demucs.separate",
        "-n",
        "htdemucs",
        "--device",
        "cpu",
        "--out",
        str(output_root),
        str(source_loop),
    ]
    env = os.environ.copy()
    env["DEMUCS_OFFLINE"] = "1"
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT_DIR), env=env, check=False)
    stem_dir = _first_stem_dir(output_root)
    readable = _readable_stems(stem_dir)
    active = proc.returncode == 0 and len(readable) >= 2
    return {
        "model": "demucs",
        "active": active,
        "status": "active" if active else "failed",
        "reason": "" if active else f"return_code_{proc.returncode}",
        "checkpoint_hits": checkpoint_hits,
        "readable_stems": [Path(item).relative_to(ROOT_DIR).as_posix() for item in readable if item.startswith(str(ROOT_DIR))],
        "smoke_output_root": output_root.relative_to(ROOT_DIR).as_posix(),
        "command": "python -m demucs.separate -n htdemucs --device cpu --out local_model_outputs/demucs local_model_outputs/source_loop.wav",
        "stdout_tail": _redact_text(proc.stdout[-1200:]),
        "stderr_tail": _redact_text(proc.stderr[-1200:]),
        "real_backend_observation": 1 if active else 0,
        "cloud_called": False,
    }


def _symbolic_status(name: str, module_name: str, note: str) -> dict[str, Any]:
    available = _module_available(module_name)
    return {
        "model": name,
        "active": False,
        "status": "blocked",
        "official_source": note,
        "license": "unknown_requires_manual_verification",
        "checkpoint_local": False,
        "local_inference_feasible": bool(available),
        "smoke_output_generated": False,
        "reason": "missing_local_checkpoint_or_config" if available else f"python_module_missing_{module_name}",
        "real_backend_observation": 0,
        "cloud_called": False,
    }


def _mt3_status(basicpitch_result: dict[str, Any]) -> dict[str, Any]:
    available = _module_available("mt3") or _module_available("yourmt3")
    parse_compare = {
        "basicpitch_note_count": int(basicpitch_result.get("note_count", 0)),
        "basicpitch_midi_present": bool(basicpitch_result.get("smoke_output_midi")),
    }
    return {
        "model": "mt3",
        "active": False,
        "status": "blocked",
        "official_source": "google-research/mt3 (YourMT3 variants exist in forks)",
        "license": "apache-2.0_or_fork_specific",
        "checkpoint_local": False,
        "local_inference_feasible": bool(available),
        "smoke_output_generated": False,
        "parse_comparison_to_basicpitch": parse_compare,
        "reason": "no_verified_local_checkpoint_and_configured_runtime",
        "real_backend_observation": 0,
        "cloud_called": False,
    }


def _omnizart_status() -> dict[str, Any]:
    available = _module_available("omnizart")
    return {
        "model": "omnizart",
        "active": False,
        "status": "blocked",
        "official_source": "Music-and-Culture-Technology-Lab/omnizart",
        "license": "mit",
        "checkpoint_local": False,
        "local_inference_feasible": bool(available),
        "smoke_output_generated": False,
        "reason": "local_checkpoint_not_configured",
        "real_backend_observation": 0,
        "cloud_called": False,
    }


def _moonbeam_status(basicpitch_result: dict[str, Any]) -> dict[str, Any]:
    available = _module_available("moonbeam")
    return {
        "model": "moonbeam",
        "active": False,
        "status": "blocked",
        "official_source": "moonbeam symbolic model (external repository required)",
        "weights_present": False,
        "tokenizer_present": False,
        "local_inference_feasible": bool(available),
        "input_midi_required": True,
        "input_midi_path": basicpitch_result.get("smoke_output_midi", ""),
        "smoke_output_generated": False,
        "reason": "module_or_weights_or_tokenizer_not_ready",
        "real_backend_observation": 0,
        "cloud_called": False,
    }


def _model_registry_rows(results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model_name in MODEL_ORDER:
        row = results[model_name]
        adapter_path = ""
        if model_name in {"basicpitch", "mt3"}:
            adapter_path = "features/model_integrations/locked_model_adapters.py::transcribe_audio"
        elif model_name == "demucs":
            adapter_path = "features/model_integrations/locked_model_adapters.py::separate_audio"
        else:
            adapter_path = "features/model_integrations/locked_model_adapters.py::analyze_midi|generate_midi_context"
        rows.append(
            {
                "model": model_name,
                "active": bool(row.get("active", False)),
                "status": str(row.get("status", "unknown")),
                "reason": str(row.get("reason", "")),
                "adapter_path": adapter_path,
                "real_backend_observation": int(row.get("real_backend_observation", 0)),
                "can_use_in_loop_quality_pipeline": bool(row.get("active", False)),
            }
        )
    return rows


def _write_named_report(stem: str, payload: dict[str, Any], title: str) -> None:
    json_path = REPORT_DIR / f"{stem}.json"
    md_path = REPORT_DIR / f"{stem}.md"
    _write_json(json_path, payload)
    lines = [f"# {title}", "", f"- generated_at: `{payload.get('generated_at', '')}`"]
    for key, value in payload.items():
        if key == "generated_at":
            continue
        lines.append(f"- {key}: `{value}`")
    _write_md(md_path, lines)


def run_lock_campaign() -> dict[str, Any]:
    _ensure_local_roots()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    source_loop = LOCAL_OUTPUTS / "source_loop.wav"
    source_meta = _build_source_loop(source_loop)

    basicpitch = _run_basicpitch_smoke(source_loop)
    demucs = _run_demucs_smoke(source_loop)
    mt3 = _mt3_status(basicpitch)
    omnizart = _omnizart_status()
    moonbeam = _moonbeam_status(basicpitch)
    musicbert = _symbolic_status("musicbert", "transformers", "facebookresearch/musicbert")
    midigpt = _symbolic_status("midigpt", "midigpt", "midigpt project")
    text2midi = _symbolic_status("text2midi", "text2midi", "text2midi project")

    all_results = {
        "basicpitch": basicpitch,
        "demucs": demucs,
        "mt3": mt3,
        "omnizart": omnizart,
        "moonbeam": moonbeam,
        "musicbert": musicbert,
        "midigpt": midigpt,
        "text2midi": text2midi,
    }
    blockers = [f"{name}:{row['reason']}" for name, row in all_results.items() if not row.get("active", False)]

    plan_payload = {
        "generated_at": _timestamp(),
        "freeze_generation": True,
        "paused_flags": {
            "generation_paused": True,
            "reroll_paused": True,
            "product_pack_creation_paused": True,
            "cloud_calls_paused": True,
        },
        "active_models": [name for name, row in all_results.items() if row.get("active", False)],
        "inactive_models": [name for name, row in all_results.items() if not row.get("active", False)],
        "blockers": blockers,
        "priority_order": MODEL_ORDER,
        "constraints_acknowledged": [
            "no_branches_or_worktrees",
            "no_stash_apply_or_drop",
            "no_generation_or_reroll_runs",
            "no_training_or_cloud_calls",
        ],
    }
    _write_named_report("model_integration_lock_plan", plan_payload, "Model Integration Lock Plan")

    env_strategy = {
        "generated_at": _timestamp(),
        "local_env_roots": [f".local_model_envs/{name}" for name in ENV_ROOTS],
        "ignore_required": [
            ".local_model_envs/",
            "local_model_weights/",
            "local_model_cache/",
            "local_model_outputs/",
        ],
        "policy": "never_commit_local_env_artifacts_or_weights_or_outputs",
    }
    _write_named_report("model_environment_strategy", env_strategy, "Model Environment Strategy")

    for stem, title, payload in [
        ("basicpitch_integration_report", "BasicPitch Integration Report", basicpitch),
        ("demucs_integration_report", "Demucs Integration Report", demucs),
        ("mt3_integration_report", "MT3 Integration Report", mt3),
        ("omnizart_integration_report", "Omnizart Integration Report", omnizart),
        ("moonbeam_integration_report", "Moonbeam Integration Report", moonbeam),
        ("musicbert_integration_report", "MusicBERT Integration Report", musicbert),
        ("midigpt_integration_report", "MIDI-GPT Integration Report", midigpt),
        ("text2midi_integration_report", "Text2MIDI Integration Report", text2midi),
    ]:
        payload = {"generated_at": _timestamp(), **payload}
        _write_named_report(stem, payload, title)

    registry_rows = _model_registry_rows(all_results)
    local_registry_payload = {
        "generated_at": _timestamp(),
        "source_loop": source_meta,
        "models": registry_rows,
    }
    _write_json(LOCAL_REGISTRY, local_registry_payload)

    redacted_registry = {
        "generated_at": _timestamp(),
        "models": registry_rows,
        "redaction": {
            "local_absolute_paths": "removed",
            "only_repo_relative_paths_or_flags": True,
        },
    }
    _write_named_report("active_model_registry_report", redacted_registry, "Active Model Registry Report")

    additional_active = any(all_results[name].get("active", False) for name in ["mt3", "omnizart", *SYMBOLIC_MODELS])
    minimum_ready = bool(basicpitch.get("active", False) and demucs.get("active", False) and additional_active)
    final_lock = {
        "generated_at": _timestamp(),
        "minimum_stack_logic": {
            "basicpitch_active_true": bool(basicpitch.get("active", False)),
            "demucs_active_true": bool(demucs.get("active", False)),
            "one_additional_transcription_or_symbolic_active_true": bool(additional_active),
            "zero_new_privacy_leaks": None,
            "adapters_integrated": True,
            "tests_pass": None,
        },
        "minimum_stack_ready_for_quality_generation": minimum_ready,
        "blockers": blockers if not minimum_ready else [],
        "generation_allowed": False,
    }
    _write_named_report("model_integration_lock", final_lock, "Final Model Integration Lock")
    return {
        "source_loop": source_meta,
        "results": all_results,
        "blockers": blockers,
        "minimum_ready": minimum_ready,
    }


def main() -> int:
    payload = run_lock_campaign()
    print(f"SOURCE_LOOP={payload['source_loop']['path']}")
    print(f"BASICPITCH_ACTIVE={payload['results']['basicpitch']['active']}")
    print(f"DEMUCS_ACTIVE={payload['results']['demucs']['active']}")
    print(f"MINIMUM_READY={payload['minimum_ready']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
