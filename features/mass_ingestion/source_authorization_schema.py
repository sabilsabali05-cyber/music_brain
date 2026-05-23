from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ALLOWED_TRAINING_SOURCES = {"production", "retrieval", "synplant_seed"}


@dataclass(frozen=True)
class AuthorizationValidationResult:
    status: str
    errors: list[str]
    warnings: list[str]
    training_authorized_count: int
    excluded_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "training_authorized_count": self.training_authorized_count,
            "excluded_count": self.excluded_count,
        }


def validate_source_authorization(payload: dict[str, Any]) -> AuthorizationValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    training_authorized_count = 0
    excluded_count = 0

    song_files = payload.get("song_files", [])
    if not isinstance(song_files, list):
        errors.append("song_files must be a list.")
        song_files = []

    for index, item in enumerate(song_files):
        if not isinstance(item, dict):
            errors.append(f"song_files[{index}] must be an object.")
            continue
        source = str(item.get("source", "")).strip().lower()
        training_allowed = bool(item.get("training_allowed", False))
        excluded = bool(item.get("excluded", False))
        authorization = str(item.get("authorization", "")).strip().lower()
        if not authorization:
            warnings.append(f"song_files[{index}] missing explicit authorization note.")
        if "splice" in source:
            if training_allowed:
                errors.append(f"song_files[{index}] cannot use Splice with training_allowed=true.")
            else:
                warnings.append(f"song_files[{index}] is Splice and retained for non-training usage only.")
        if training_allowed and source not in ALLOWED_TRAINING_SOURCES:
            errors.append(
                f"song_files[{index}] source={source or 'unknown'} is not allowed for training. "
                f"Allowed: {sorted(ALLOWED_TRAINING_SOURCES)}."
            )
        if excluded:
            excluded_count += 1
        if training_allowed and not excluded:
            training_authorized_count += 1

    sample_filters = payload.get("sample_library_filters", [])
    if isinstance(sample_filters, list):
        for index, item in enumerate(sample_filters):
            if not isinstance(item, dict):
                errors.append(f"sample_library_filters[{index}] must be an object.")
                continue
            source = str(item.get("source", "")).strip().lower()
            training_allowed = bool(item.get("training_allowed", False))
            if "splice" in source and training_allowed:
                errors.append(f"sample_library_filters[{index}] cannot use Splice with training_allowed=true.")
            if training_allowed and source not in ALLOWED_TRAINING_SOURCES:
                errors.append(
                    f"sample_library_filters[{index}] source={source or 'unknown'} is not allowed for training."
                )
    else:
        errors.append("sample_library_filters must be a list.")

    status = "invalid" if errors else "valid"
    return AuthorizationValidationResult(
        status=status,
        errors=errors,
        warnings=warnings,
        training_authorized_count=training_authorized_count,
        excluded_count=excluded_count,
    )
