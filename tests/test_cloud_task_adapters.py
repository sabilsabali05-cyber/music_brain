from __future__ import annotations

from features.cloud_execution.task_adapters import (
    basic_pitch_cloud_task,
    demucs_cloud_task,
    essentia_cloud_task,
    mert_cloud_task,
    midigpt_cloud_task,
    moonbeam_cloud_task,
    muq_cloud_task,
    musicbert_cloud_task,
    text2midi_cloud_task,
    yourmt3_cloud_task,
)

ADAPTERS = [
    demucs_cloud_task,
    essentia_cloud_task,
    muq_cloud_task,
    mert_cloud_task,
    yourmt3_cloud_task,
    basic_pitch_cloud_task,
    text2midi_cloud_task,
    moonbeam_cloud_task,
    midigpt_cloud_task,
    musicbert_cloud_task,
]


def test_adapters_expose_required_functions() -> None:
    for adapter in ADAPTERS:
        for fn_name in ("describe_task", "estimate_cost", "validate_inputs", "plan_job", "run_job"):
            assert hasattr(adapter, fn_name)


def test_adapters_default_to_skipped_dry_run() -> None:
    for adapter in ADAPTERS:
        result = adapter.run_job({"execute": False, "provider_id": "modal", "input_id": "i1"}).as_dict()
        assert result["status"] == "skipped_dry_run"
        assert result["job_started"] is False
        assert result["upload_performed"] is False
        assert result["download_performed"] is False
