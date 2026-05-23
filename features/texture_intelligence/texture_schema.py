from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SpectralTextureProfile:
    brightness: float = 0.0
    spectral_centroid: float = 0.0
    spectral_flatness: float = 0.0
    harmonicity: float = 0.0
    noise_ratio: float = 0.0
    graininess: float = 0.0
    roughness: float = 0.0


@dataclass
class TransientEnvelopeProfile:
    attack_sharpness: float = 0.0
    decay_length: float = 0.0
    sustain_behavior: Literal["short", "medium", "long", "unknown"] = "unknown"
    transient_density: float = 0.0


@dataclass
class TonalityTextureProfile:
    pitch_stability: float = 0.0
    harmonicity: float = 0.0
    breathiness: float = 0.0


@dataclass
class MotionTextureProfile:
    modulation_motion: float = 0.0
    movement_shape: Literal["static", "slow_evolving", "rhythmic", "chaotic", "unknown"] = "unknown"
    novelty_score: float = 0.0


@dataclass
class NoiseTextureProfile:
    noise_ratio: float = 0.0
    graininess: float = 0.0
    breathiness: float = 0.0
    roughness: float = 0.0


@dataclass
class SoundRoleHypothesis:
    role_name: str
    fit_to_role_score: float
    evidence: list[str] = field(default_factory=list)


@dataclass
class SynplantSeedFitPrediction:
    synplant_seed_promise: float
    recommended_seed_strategy: Literal["manual", "assisted", "not_recommended"] = "manual"
    reasoning: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class SoundContextFit:
    track_role: str
    fit_to_role_score: float
    fit_to_mix_score: float
    novelty_score: float
    masking_risk_score: float = 0.0
    contrast_pair_candidates: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class TextureFingerprint:
    sample_id: str
    asset_type_guess: str
    source_policy: str
    spectral_profile: SpectralTextureProfile = field(default_factory=SpectralTextureProfile)
    transient_profile: TransientEnvelopeProfile = field(default_factory=TransientEnvelopeProfile)
    tonality_profile: TonalityTextureProfile = field(default_factory=TonalityTextureProfile)
    motion_profile: MotionTextureProfile = field(default_factory=MotionTextureProfile)
    noise_profile: NoiseTextureProfile = field(default_factory=NoiseTextureProfile)
    role_candidates: list[SoundRoleHypothesis] = field(default_factory=list)
    synplant_seed_fit: SynplantSeedFitPrediction = field(default_factory=lambda: SynplantSeedFitPrediction(0.0))
    created_at: str = field(default_factory=now_iso)
    limitations: list[str] = field(default_factory=list)


@dataclass
class SoundPaletteContext:
    project_id: str
    foreground_roles: list[str] = field(default_factory=list)
    background_roles: list[str] = field(default_factory=list)
    low_spectral_occupancy_roles: list[str] = field(default_factory=list)
    mid_spectral_occupancy_roles: list[str] = field(default_factory=list)
    high_spectral_occupancy_roles: list[str] = field(default_factory=list)
    density_by_section: dict[str, float] = field(default_factory=dict)
    contrast_pairs: list[str] = field(default_factory=list)
    masking_risks: list[str] = field(default_factory=list)
    missing_texture_roles: list[str] = field(default_factory=list)
    suggested_additions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class TextureTrainingCandidate:
    sample_id: str
    source_policy: Literal[
        "user_owned_training_candidate",
        "production_only_training_excluded",
        "splice_production_only",
        "unknown_blocked",
    ]
    training_allowed: bool
    production_use_allowed: bool
    context_fit: SoundContextFit
    fingerprint: TextureFingerprint
    limitations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)
