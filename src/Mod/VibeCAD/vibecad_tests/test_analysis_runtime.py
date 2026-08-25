# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import annotations

from dataclasses import dataclass

import pytest

from VibeCADAnalysisRuntime import AnalysisRuntime, AnalysisRuntimeError


@dataclass
class _Snapshot:
    job_id: str = "job-1"
    document_uid: str = "doc-1"
    capability_name: str = "analyze.solver_execution.run"


class _Manager:
    def __init__(self) -> None:
        self.submissions: list[dict[str, object]] = []
        self.cancelled: list[str] = []
        self.snapshot_value = _Snapshot()

    def submit(self, **kwargs):
        self.submissions.append(dict(kwargs))
        return self.snapshot_value

    def snapshot(self, job_id: str):
        assert job_id == self.snapshot_value.job_id
        return self.snapshot_value

    def cancel(self, job_id: str) -> bool:
        self.cancelled.append(job_id)
        return True


def test_analysis_runtime_forwards_exact_background_submission_contract() -> None:
    manager = _Manager()
    dispatch = lambda callback: callback()
    runtime = AnalysisRuntime(
        manager,
        document_uid="doc-1",
        dispatch_to_document_thread=dispatch,
    )
    prepare = lambda cancelled, progress: (cancelled, progress)
    validate = lambda: None
    commit = lambda prepared: {"prepared": prepared}
    cleanup = lambda prepared: None

    snapshot = runtime.submit(
        capability_name="analyze.solver_execution.run",
        prepare=prepare,
        validate_before_commit=validate,
        commit=commit,
        finalize_message="Importing verified FEM results",
        cleanup=cleanup,
    )

    assert snapshot is manager.snapshot_value
    assert manager.submissions == [
        {
            "document_uid": "doc-1",
            "capability_name": "analyze.solver_execution.run",
            "prepare": prepare,
            "validate_before_commit": validate,
            "commit": commit,
            "dispatch_to_document_thread": dispatch,
            "finalize_message": "Importing verified FEM results",
            "cleanup": cleanup,
        }
    ]


def test_analysis_runtime_status_and_cancel_remain_manager_compatible() -> None:
    manager = _Manager()
    runtime = AnalysisRuntime(manager, document_uid="doc-1")

    assert runtime.snapshot("job-1") is manager.snapshot_value
    assert runtime.cancel("job-1") is True
    assert manager.cancelled == ["job-1"]


def test_analysis_runtime_requires_dispatch_only_for_submission() -> None:
    manager = _Manager()
    runtime = AnalysisRuntime(manager, document_uid="doc-1")

    with pytest.raises(AnalysisRuntimeError, match="document-thread dispatcher"):
        runtime.submit(
            capability_name="analyze.solve",
            prepare=lambda _cancelled, _progress: None,
            validate_before_commit=lambda: None,
            commit=lambda _prepared: {},
        )


def test_analysis_runtime_rejects_invalid_host_identity_and_callbacks() -> None:
    manager = _Manager()
    with pytest.raises(AnalysisRuntimeError, match="document UID"):
        AnalysisRuntime(manager, document_uid="")

    runtime = AnalysisRuntime(
        manager,
        document_uid="doc-1",
        dispatch_to_document_thread=lambda callback: callback(),
    )
    with pytest.raises(TypeError, match="callbacks"):
        runtime.submit(
            capability_name="analyze.solve",
            prepare=None,
            validate_before_commit=lambda: None,
            commit=lambda _prepared: {},
        )
