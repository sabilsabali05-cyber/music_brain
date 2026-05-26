from __future__ import annotations

import json
from pathlib import Path

from scripts import export_paired_loop_pack, verify_paired_loop_pack


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _patch_paths(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(export_paired_loop_pack, "ROOT_DIR", root)
    monkeypatch.setattr(export_paired_loop_pack, "SOURCE_CANDIDATES_JSONL", root / "datasets" / "source_sample_pack" / "source_loop_candidates.jsonl")
    monkeypatch.setattr(export_paired_loop_pack, "OUTPUT_ROOT", root / "outputs" / "paired_loop_packs")
    monkeypatch.setattr(export_paired_loop_pack, "REPORT_DIR", root / "reports" / "paired_loop_packs")
    monkeypatch.setattr(export_paired_loop_pack, "EXPORT_REPORT_JSON", export_paired_loop_pack.REPORT_DIR / "paired_loop_pack_export_report.json")
    monkeypatch.setattr(export_paired_loop_pack, "EXPORT_REPORT_MD", export_paired_loop_pack.REPORT_DIR / "paired_loop_pack_export_report.md")

    monkeypatch.setattr(verify_paired_loop_pack, "ROOT_DIR", root)
    monkeypatch.setattr(verify_paired_loop_pack, "OUTPUT_ROOT", root / "outputs" / "paired_loop_packs")
    monkeypatch.setattr(verify_paired_loop_pack, "REPORT_DIR", root / "reports" / "paired_loop_packs")
    monkeypatch.setattr(verify_paired_loop_pack, "VERIFY_REPORT_JSON", verify_paired_loop_pack.REPORT_DIR / "paired_loop_pack_verification_report.json")
    monkeypatch.setattr(verify_paired_loop_pack, "VERIFY_REPORT_MD", verify_paired_loop_pack.REPORT_DIR / "paired_loop_pack_verification_report.md")


def _seed_candidate_rows() -> list[dict]:
    rows = []
    roles = ["bass", "melody", "melody", "texture", "drums"]
    for idx, role in enumerate(roles):
        rows.append(
            {
                "candidate_id": f"c{idx + 1}",
                "source_id": f"s{idx + 1}",
                "source_redacted_path": "<PRIVATE_LOCAL_PATH>/demo.wav",
                "role": role,
                "bar_length": 4,
                "bpm_estimate": 120.0,
                "key_estimate": "C",
                "witness_ids": ["heuristic_local_features"],
            }
        )
    return rows


def test_export_produces_family_variation_pack(monkeypatch, tmp_path: Path) -> None:
    _patch_paths(monkeypatch, tmp_path)
    _write_jsonl(tmp_path / "datasets" / "source_sample_pack" / "source_loop_candidates.jsonl", _seed_candidate_rows())

    report = export_paired_loop_pack._family_export(
        export_paired_loop_pack._FamilyArgs(
            family_count=4,
            variations_per_family=6,
            roles=["bass", "chords", "lead", "texture"],
            include_seed=True,
            render_audio=True,
            preview=True,
        )
    )
    pack_root = tmp_path / report["pack_path"]
    verify = verify_paired_loop_pack.verify_pack(pack_root)

    assert report["family_count"] >= 4
    assert report["variation_count"] >= 28
    assert report["midi_count"] == report["pair_json_count"]
    assert report["wav_count"] == report["pair_json_count"]
    assert report["render_verified_count"] == report["pair_json_count"]
    assert verify["pack_verified"] is True
    assert verify["audio_orphan_count"] == 0
    assert verify["clone_variation_failures"] == 0
    assert verify["family_count"] >= 4
    assert verify["pair_json_count"] >= 28

    manifest = json.loads((pack_root / "pack_manifest.json").read_text(encoding="utf-8"))
    assert manifest["pair_json_count"] == report["pair_json_count"]
    assert "C:/Users/" not in json.dumps(manifest)
    assert "C:\\Users\\" not in json.dumps(manifest)
    readme_text = (pack_root / "PACK_README.md").read_text(encoding="utf-8")
    assert "Family structure" in readme_text
    assert "Derivative policy" in readme_text

    for family in manifest["families"]:
        family_manifest = json.loads((tmp_path / family["family_manifest_path"]).read_text(encoding="utf-8"))
        assert family_manifest["seed_pair_count"] >= 1
        assert family_manifest["variation_pair_count"] >= 3
        hashes: dict[str, str] = {}
        for pair_ref in family_manifest["pairs"]:
            pair = json.loads((tmp_path / pair_ref["pair_path"]).read_text(encoding="utf-8"))
            midi_path = tmp_path / pair["midi_path"]
            wav_path = tmp_path / pair["wav_path"]
            assert midi_path.exists()
            assert wav_path.exists()
            assert wav_path.stat().st_size > 44
            assert pair["transformation_from_seed"]
            assert pair["musical_independence_note"]
            assert pair["source_explanation"]
            hashes[pair["variation_type"]] = pair["note_event_hash"]
        seed_hash = hashes["seed"]
        for variation_type, hash_value in hashes.items():
            if variation_type == "seed":
                continue
            assert hash_value != seed_hash


def test_clone_variation_fails_verification(monkeypatch, tmp_path: Path) -> None:
    _patch_paths(monkeypatch, tmp_path)
    _write_jsonl(tmp_path / "datasets" / "source_sample_pack" / "source_loop_candidates.jsonl", _seed_candidate_rows())
    report = export_paired_loop_pack._family_export(
        export_paired_loop_pack._FamilyArgs(
            family_count=3,
            variations_per_family=4,
            roles=["bass", "chords", "lead", "texture"],
            include_seed=True,
            render_audio=True,
            preview=True,
        )
    )
    pack_root = tmp_path / report["pack_path"]
    manifest = json.loads((pack_root / "pack_manifest.json").read_text(encoding="utf-8"))
    first_family_manifest_path = tmp_path / manifest["families"][0]["family_manifest_path"]
    first_family_manifest = json.loads(first_family_manifest_path.read_text(encoding="utf-8"))
    seed_pair_path = tmp_path / first_family_manifest["pairs"][0]["pair_path"]
    clone_pair_path = tmp_path / first_family_manifest["pairs"][1]["pair_path"]
    seed_pair = json.loads(seed_pair_path.read_text(encoding="utf-8"))
    clone_pair = json.loads(clone_pair_path.read_text(encoding="utf-8"))

    (tmp_path / clone_pair["midi_path"]).write_bytes((tmp_path / seed_pair["midi_path"]).read_bytes())
    verify = verify_paired_loop_pack.verify_pack(pack_root)
    assert verify["pack_verified"] is False
    assert verify["clone_variation_failures"] >= 1
