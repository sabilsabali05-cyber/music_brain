from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DemucsAvailability:
    configured: bool
    available: bool
    unavailable_reason: str
    package_required: str
    model_name: str
    device: str
    output_dir: str
    stem_policy: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "available": self.available,
            "unavailable_reason": self.unavailable_reason,
            "package_required": self.package_required,
            "model_name": self.model_name,
            "device": self.device,
            "output_dir": self.output_dir,
            "stem_policy": self.stem_policy,
        }


def demucs_unavailable_safe(settings: dict[str, Any], using_local_config: bool) -> DemucsAvailability:
    demucs_cfg = settings.get("demucs", {})
    demucs_cfg = demucs_cfg if isinstance(demucs_cfg, dict) else {}
    enabled = bool(demucs_cfg.get("enabled", False)) if using_local_config else False
    package_required = str(demucs_cfg.get("package_required", "demucs"))
    model_name = str(demucs_cfg.get("model_name", "htdemucs"))
    device = str(demucs_cfg.get("device", "<DEVICE>"))
    output_dir = str(demucs_cfg.get("output_dir", "<PATH_TO_REPO>"))
    stem_policy = str(demucs_cfg.get("stem_policy", "weak_evidence_not_truth"))

    if not using_local_config:
        reason = "disabled_or_missing_local_config"
    elif not enabled:
        reason = "disabled_in_local_config"
    else:
        reason = "configured_but_execution_disabled_by_policy"

    return DemucsAvailability(
        configured=using_local_config and enabled,
        available=False,
        unavailable_reason=reason,
        package_required=package_required,
        model_name=model_name,
        device=device,
        output_dir=output_dir,
        stem_policy=stem_policy,
    )
