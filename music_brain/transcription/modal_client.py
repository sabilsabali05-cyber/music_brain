from __future__ import annotations

from collections.abc import Callable

from .base import BaseTranscriber, TranscriptionRequest, TranscriptionResult

RemoteCall = Callable[[bytes], dict[str, object]]


class ModalFakeTranscriber(BaseTranscriber):
    def __init__(
        self,
        endpoint: str | None,
        remote_call: RemoteCall | None = None,
    ) -> None:
        self.endpoint = endpoint
        self._remote_call = remote_call

    def _invoke_modal(self, normalized_audio_bytes: bytes) -> dict[str, object]:
        if self._remote_call is not None:
            return self._remote_call(normalized_audio_bytes)

        try:
            import modal  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "modal package is required for backend=modal_fake. Install dependencies and run `modal setup`."
            ) from exc

        function = modal.Function.from_name("music-brain-v2", "remote_fake_transcribe")
        return function.remote(normalized_audio_bytes)

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        audio_bytes = request.normalized_audio_path.read_bytes()
        payload = self._invoke_modal(audio_bytes)

        midi_bytes_raw = payload.get("midi_bytes")
        if not isinstance(midi_bytes_raw, (bytes, bytearray)):
            raise RuntimeError("Modal response is missing valid midi_bytes")
        midi_bytes = bytes(midi_bytes_raw)

        request.output_midi_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_midi_path.write_bytes(midi_bytes)

        provider_used = str(payload.get("provider_used", "fake"))
        backend = str(payload.get("backend", "modal_fake"))
        model_version = str(payload.get("model_version", "modal-fake-transcriber-v0"))

        if provider_used != "fake" or backend != "modal_fake":
            raise RuntimeError(
                "Modal fake backend returned unexpected identity metadata: "
                f"provider_used={provider_used}, backend={backend}"
            )

        return TranscriptionResult(
            provider_used="fake",
            backend="modal_fake",
            model_version=model_version,
            fallback_used=False,
            fallback_reason=None,
        )
