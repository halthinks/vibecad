# SPDX-License-Identifier: LGPL-2.1-or-later

"""Host-owned orchestration seam for VibeCAD Analysis computations.

This is intentionally a strangler facade over the proven background manager.
It owns no solver physics, CAD mutation, persistence, qualification, or new
concurrency policy. During migration it forwards the exact prepare -> worker ->
document-thread commit contract so callers can move behind a host Analysis API
without introducing a parallel scheduler.
"""

from __future__ import annotations

from typing import Any, Callable


class AnalysisRuntimeError(RuntimeError):
    """The host Analysis orchestration seam is configured incorrectly."""


PrepareHandler = Callable[[Callable[[], bool], Callable[[int, str], None]], Any]
CommitValidator = Callable[[], Any]
CommitHandler = Callable[[Any], Any]
CleanupHandler = Callable[[Any | None], None]
DocumentThreadDispatcher = Callable[[Callable[[], Any]], Any]


class AnalysisRuntime:
    """Forward Analysis lifecycle operations through one existing job authority."""

    def __init__(
        self,
        job_manager: Any,
        *,
        document_uid: str,
        dispatch_to_document_thread: DocumentThreadDispatcher | None = None,
    ) -> None:
        uid = str(document_uid or "").strip()
        if not uid:
            raise AnalysisRuntimeError("Analysis Runtime requires an exact document UID.")
        if job_manager is None:
            raise AnalysisRuntimeError("Analysis Runtime requires a job manager.")
        for operation in ("submit", "snapshot", "cancel"):
            if not callable(getattr(job_manager, operation, None)):
                raise AnalysisRuntimeError(
                    f"Analysis Runtime job manager lacks {operation}()."
                )
        if dispatch_to_document_thread is not None and not callable(
            dispatch_to_document_thread
        ):
            raise TypeError("dispatch_to_document_thread must be callable")
        self._job_manager = job_manager
        self._document_uid = uid
        self._dispatch_to_document_thread = dispatch_to_document_thread

    @property
    def document_uid(self) -> str:
        return self._document_uid

    def submit(
        self,
        *,
        capability_name: str,
        prepare: PrepareHandler,
        validate_before_commit: CommitValidator,
        commit: CommitHandler,
        finalize_message: str | None = None,
        cleanup: CleanupHandler | None = None,
    ) -> Any:
        capability = str(capability_name or "").strip()
        if not capability:
            raise AnalysisRuntimeError(
                "Analysis Runtime submission requires a capability name."
            )
        if not all(
            callable(callback)
            for callback in (prepare, validate_before_commit, commit)
        ):
            raise TypeError("Analysis Runtime lifecycle callbacks must be callable")
        if cleanup is not None and not callable(cleanup):
            raise TypeError("cleanup must be callable")
        dispatcher = self._dispatch_to_document_thread
        if dispatcher is None:
            raise AnalysisRuntimeError(
                "Analysis Runtime submission requires a document-thread dispatcher."
            )
        return self._job_manager.submit(
            document_uid=self._document_uid,
            capability_name=capability,
            prepare=prepare,
            validate_before_commit=validate_before_commit,
            commit=commit,
            dispatch_to_document_thread=dispatcher,
            finalize_message=finalize_message,
            cleanup=cleanup,
        )

    def snapshot(self, job_id: str) -> Any:
        clean = str(job_id or "").strip()
        if not clean:
            raise AnalysisRuntimeError("Analysis Runtime job lookup requires a job ID.")
        return self._job_manager.snapshot(clean)

    def cancel(self, job_id: str) -> bool:
        clean = str(job_id or "").strip()
        if not clean:
            raise AnalysisRuntimeError("Analysis Runtime cancellation requires a job ID.")
        return bool(self._job_manager.cancel(clean))
