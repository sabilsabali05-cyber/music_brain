from __future__ import annotations

import importlib
import os
import platform
import shutil
import sys
from pathlib import Path

from music_brain.config import AppConfig, load_config
from music_brain.schemas import PreflightCheck, PreflightReport
from music_brain.transcription import create_transcriber
from music_brain.transcription.fake import FakeTranscriber
from music_brain.transcription.modal_client import ModalFakeTranscriber
from music_brain.transcription.yourmt3_modal_client import YourMT3ModalTranscriber


def _can_write_to_dir(directory: Path) -> bool:
    probe = directory / ".music_brain_write_test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def run_preflight() -> PreflightReport:
    checks: list[PreflightCheck] = []
    provider = "unknown"
    backend = "unknown"
    library_root = Path("library")
    config: AppConfig | None = None

    python_ok = sys.version_info >= (3, 10)
    checks.append(
        PreflightCheck(
            name="python_version",
            ok=python_ok,
            message=f"Python {platform.python_version()} (requires >= 3.10)",
        )
    )

    cwd = Path.cwd()
    checks.append(
        PreflightCheck(
            name="cwd",
            ok=True,
            message=str(cwd),
        )
    )

    try:
        importlib.import_module("music_brain")
        checks.append(PreflightCheck(name="project_import", ok=True, message="Import succeeded"))
    except Exception as exc:  # noqa: BLE001
        checks.append(
            PreflightCheck(
                name="project_import",
                ok=False,
                message=f"Import failed: {exc.__class__.__name__}: {exc}",
            )
        )

    ffmpeg_path = shutil.which("ffmpeg")
    checks.append(
        PreflightCheck(
            name="ffmpeg_on_path",
            ok=ffmpeg_path is not None,
            message=ffmpeg_path or "ffmpeg not found on PATH",
        )
    )

    try:
        config = load_config()
        provider = config.provider_requested
        backend = config.backend
        library_root = config.library_root
        checks.append(
            PreflightCheck(
                name="provider_backend_config",
                ok=True,
                message=f"provider={provider}, backend={backend}",
            )
        )
    except Exception as exc:  # noqa: BLE001
        checks.append(
            PreflightCheck(
                name="provider_backend_config",
                ok=False,
                message=f"Config error: {exc.__class__.__name__}: {exc}",
            )
        )

    if config is not None:
        try:
            config.library_root.mkdir(parents=True, exist_ok=True)
            checks.append(
                PreflightCheck(
                    name="library_create",
                    ok=True,
                    message=f"Library ready at {config.library_root.resolve().as_posix()}",
                )
            )
        except OSError as exc:
            checks.append(
                PreflightCheck(
                    name="library_create",
                    ok=False,
                    message=f"Failed to create library root: {exc}",
                )
            )

        writable = _can_write_to_dir(config.library_root)
        checks.append(
            PreflightCheck(
                name="library_write_permission",
                ok=writable,
                message=(
                    f"Writable: {config.library_root.resolve().as_posix()}"
                    if writable
                    else f"Not writable: {config.library_root.resolve().as_posix()}"
                ),
            )
        )

        if config.backend in {"modal_fake", "modal"}:
            try:
                import modal  # type: ignore[import-not-found]  # noqa: F401
                checks.append(
                    PreflightCheck(
                        name="modal_package_import",
                        ok=True,
                        message="modal package import succeeded",
                    )
                )
            except Exception as exc:  # noqa: BLE001
                checks.append(
                    PreflightCheck(
                        name="modal_package_import",
                        ok=False,
                        message=f"modal import failed: {exc.__class__.__name__}: {exc}",
                    )
                )

            has_env_auth = bool(os.getenv("MODAL_TOKEN_ID")) and bool(os.getenv("MODAL_TOKEN_SECRET"))
            has_config_auth = (Path.home() / ".modal.toml").exists()
            modal_auth_ok = has_env_auth or has_config_auth
            checks.append(
                PreflightCheck(
                    name="modal_auth_config",
                    ok=modal_auth_ok,
                    message=(
                        "Modal auth config detected"
                        if modal_auth_ok
                        else "No Modal auth detected. Run `modal setup`."
                    ),
                )
            )

            if config.backend == "modal" and config.provider_requested == "yourmt3":
                try:
                    import modal  # type: ignore[import-not-found]
                    modal.Cls.from_name("music-brain-v2", "YourMT3ModalRunner")
                    checks.append(
                        PreflightCheck(
                            name="modal_yourmt3_lookup",
                            ok=True,
                            message="Found Modal class reference music-brain-v2.YourMT3ModalRunner",
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    checks.append(
                        PreflightCheck(
                            name="modal_yourmt3_lookup",
                            ok=False,
                            message=f"Could not look up Modal YourMT3 runner: {exc.__class__.__name__}: {exc}",
                        )
                    )
                try:
                    import modal  # type: ignore[import-not-found]
                    modal.Function.from_name("music-brain-v2", "yourmt3_diagnostics")
                    checks.append(
                        PreflightCheck(
                            name="modal_yourmt3_diagnostics_lookup",
                            ok=True,
                            message="Found Modal diagnostics function music-brain-v2.yourmt3_diagnostics",
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    checks.append(
                        PreflightCheck(
                            name="modal_yourmt3_diagnostics_lookup",
                            ok=False,
                            message=f"Could not look up Modal diagnostics function: {exc.__class__.__name__}: {exc}",
                        )
                    )

        try:
            configured_transcriber = create_transcriber(
                provider_requested=config.provider_requested,
                backend=config.backend,
                modal_endpoint=config.modal_endpoint,
            )
            configured_ok = isinstance(
                configured_transcriber,
                (FakeTranscriber, ModalFakeTranscriber, YourMT3ModalTranscriber),
            )
            checks.append(
                PreflightCheck(
                    name="configured_backend_usable",
                    ok=configured_ok,
                    message=(
                        f"Configured transcriber: {configured_transcriber.__class__.__name__}"
                        if configured_ok
                        else "Configured transcriber has unexpected type"
                    ),
                )
            )
        except Exception as exc:  # noqa: BLE001
            checks.append(
                PreflightCheck(
                    name="configured_backend_usable",
                    ok=False,
                    message=f"Configured backend check failed: {exc.__class__.__name__}: {exc}",
                )
            )

    overall_ok = all(check.ok for check in checks)
    return PreflightReport(
        ok=overall_ok,
        checks=checks,
        python_version=platform.python_version(),
        cwd=str(cwd),
        provider=provider,
        backend=backend,
        library_root=library_root.resolve().as_posix(),
    )
