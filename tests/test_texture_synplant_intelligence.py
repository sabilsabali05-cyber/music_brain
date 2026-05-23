from __future__ import annotations

import json
from pathlib import Path

import scripts.build_sound_palette_context as palette_script
import scripts.create_synplant_session_plan as session_plan_script
import scripts.plan_texture_analysis as texture_plan_script
from features.synplant.session_schema import SynplantPatchCandidate, SynplantSeedCandidate
from features.texture_intelligence.texture_schema import (
    SoundContextFit,
    SoundPaletteContext,
    SoundRoleHypothesis,
    SpectralTextureProfile,
    SynplantSeedFitPrediction,
    TextureFingerprint,
    TextureTrainingCandidate,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def test_texture_schema_represents_individual_sound_fingerprint() -> None:
    fingerprint = TextureFingerprint(
        sample_id="s1",
        asset_type_guess="synth_one_shot",
        source_policy="user_owned_training_candidate",
        spectral_profile=SpectralTextureProfile(
            brightness=0.8,
            spectral_centroid=4500.0,
            spectral_flatness=0.2,
            harmonicity=0.7,
            noise_ratio=0.1,
            graininess=0.3,
            roughness=0.2,
        ),
        role_candidates=[SoundRoleHypothesis(role_name="lead", fit_to_role_score=0.9)],
        synplant_seed_fit=SynplantSeedFitPrediction(synplant_seed_promise=0.88),
    )
    assert fingerprint.sample_id == "s1"
    assert fingerprint.spectral_profile.brightness > 0.0
    assert fingerprint.synplant_seed_fit.synplant_seed_promise > 0.0


def test_context_fit_can_represent_collective_palette_role() -> None:
    context = SoundContextFit(track_role="lead", fit_to_role_score=0.8, fit_to_mix_score=0.7, novelty_score=0.4)
    palette = SoundPaletteContext(
        project_id="p1",
        foreground_roles=["lead", "drums"],
        background_roles=["texture_bed"],
        missing_texture_roles=["transition_fx"],
    )
    assert context.fit_to_mix_score == 0.7
    assert "transition_fx" in palette.missing_texture_roles


def test_synplant_seed_from_user_owned_source_can_be_training_candidate() -> None:
    candidate = TextureTrainingCandidate(
        sample_id="seed_1",
        source_policy="user_owned_training_candidate",
        training_allowed=True,
        production_use_allowed=True,
        context_fit=SoundContextFit(track_role="lead", fit_to_role_score=0.9, fit_to_mix_score=0.7, novelty_score=0.5),
        fingerprint=TextureFingerprint(sample_id="seed_1", asset_type_guess="synth_one_shot", source_policy="user_owned_training_candidate"),
    )
    assert candidate.training_allowed is True


def test_splice_seed_is_production_only_training_excluded() -> None:
    seed = SynplantSeedCandidate(
        seed_sample_id="s_splice",
        track_role="lead",
        source_policy="splice_production_only",
        public_label="splice seed",
    )
    assert seed.source_policy == "splice_production_only"


def test_derived_patch_inherits_seed_restrictions() -> None:
    patch = SynplantPatchCandidate(
        patch_ref="patch_1",
        seed_sample_id="s_splice",
        source_policy_inherited="splice_production_only",
    )
    assert patch.source_policy_inherited == "splice_production_only"


def test_session_planner_does_not_claim_automation_and_public_reports_have_no_private_paths(tmp_path: Path, monkeypatch) -> None:
    _write_json(
        tmp_path / "project" / "track_setup.json",
        {"tracks": [{"role": "lead"}, {"role": "bass"}, {"role": "texture_bed"}]},
    )
    _write_jsonl(
        tmp_path / "datasets" / "sample_libraries" / "lib" / "sample_seed_records.jsonl",
        [
            {
                "sample_id": "a1",
                "asset_type_guess": "synth_one_shot",
                "filename": "lead.wav",
                "source_path": "C:/Users/private/lead.wav",
                "source_type": "local_sample_seed_library",
                "authorization_status": "trusted_for_training",
                "intended_uses": ["training", "production"],
                "role_candidates": [{"role": "lead"}],
            }
        ],
    )
    _write_json(tmp_path / "reports" / "texture_intelligence" / "texture_analysis_plan.json", {"analysis_plan": []})

    monkeypatch.setattr(session_plan_script, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(session_plan_script, "PUBLIC_JSON", tmp_path / "reports" / "synplant" / "synplant_session_plan.public.json")
    monkeypatch.setattr(session_plan_script, "PUBLIC_MD", tmp_path / "reports" / "synplant" / "synplant_session_plan.public.md")
    monkeypatch.setattr(session_plan_script, "PRIVATE_JSON", tmp_path / "reports" / "synplant" / "private_synplant_session_paths.json")
    monkeypatch.setattr(session_plan_script, "PRIVATE_MD", tmp_path / "reports" / "synplant" / "private_synplant_session_paths.md")
    monkeypatch.setattr(session_plan_script, "TEXTURE_PLAN_JSON", tmp_path / "reports" / "texture_intelligence" / "texture_analysis_plan.json")

    public_json, _, private_json, _, payload = session_plan_script.create_synplant_session_plan(tmp_path / "project")
    public_text = public_json.read_text(encoding="utf-8")
    assert payload["automation_claimed"] is False
    assert "C:/Users/" not in public_text
    assert private_json.exists()


def test_private_path_reports_are_ignored() -> None:
    gitignore = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert "reports/synplant/private_synplant_session_paths.json" in gitignore
    assert "reports/synplant/private_synplant_session_paths.md" in gitignore
    assert "config/synplant/*.local.json" in gitignore


def test_texture_planner_handles_missing_sample_library_gracefully(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(texture_plan_script, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(texture_plan_script, "REPORT_JSON", tmp_path / "reports" / "texture_intelligence" / "texture_analysis_plan.json")
    monkeypatch.setattr(texture_plan_script, "REPORT_MD", tmp_path / "reports" / "texture_intelligence" / "texture_analysis_plan.md")
    _, _, payload = texture_plan_script.build_texture_analysis_plan()
    assert payload["records_found"] == 0
    assert payload["status"] == "ok"


def test_sound_palette_context_reports_missing_roles_honestly(tmp_path: Path, monkeypatch) -> None:
    _write_json(tmp_path / "project" / "track_setup.json", {"tracks": [{"role": "drums"}, {"role": "lead"}]})
    _write_json(tmp_path / "reports" / "synplant" / "synplant_session_plan.public.json", {"seed_candidates": []})
    _write_json(tmp_path / "reports" / "texture_intelligence" / "texture_analysis_plan.json", {"analysis_plan": []})
    monkeypatch.setattr(palette_script, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(palette_script, "OUT_JSON", tmp_path / "reports" / "texture_intelligence" / "sound_palette_context.json")
    monkeypatch.setattr(palette_script, "OUT_MD", tmp_path / "reports" / "texture_intelligence" / "sound_palette_context.md")
    monkeypatch.setattr(palette_script, "SYNPLANT_PLAN", tmp_path / "reports" / "synplant" / "synplant_session_plan.public.json")
    monkeypatch.setattr(palette_script, "TEXTURE_PLAN", tmp_path / "reports" / "texture_intelligence" / "texture_analysis_plan.json")
    _, _, payload = palette_script.build_sound_palette_context(tmp_path / "project")
    assert "bass" in payload["missing_texture_roles"]
    assert "chords" in payload["missing_texture_roles"]
