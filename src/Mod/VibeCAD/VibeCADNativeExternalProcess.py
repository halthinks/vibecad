# SPDX-License-Identifier: LGPL-2.1-or-later

"""Host-owned, shell-free lifecycle for cancelable external processes.

This module contains no FEM, mesh, Aero, or document semantics. Domain adapters
translate its bounded execution failures into their own capability errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import time
from typing import Any, Callable, Mapping, Sequence

from VibeCADNativeBackground import NativeBackgroundCancelled


DEFAULT_POLL_SECONDS = 0.1
DEFAULT_TAIL_BYTES = 2400


@dataclass(frozen=True, slots=True)
class NativeExternalProcessStage:
    stage: int
    program: str
    exit_code: int
    log_path: str


class NativeExternalProcessError(RuntimeError):
    """Bounded process failure for translation by a domain adapter."""

    def __init__(
        self,
        reason: str,
        *,
        stage: int,
        program: str,
        exit_code: int | None = None,
        detail: str = "",
    ) -> None:
        clean_reason = str(reason or "").strip()
        if clean_reason not in {
            "start_failed",
            "timeout",
            "output_limit",
            "backend_failed",
        }:
            raise ValueError("Unsupported external-process failure reason.")
        self.reason = clean_reason
        self.stage = int(stage)
        self.program = str(program)
        self.exit_code = None if exit_code is None else int(exit_code)
        self.detail = str(detail or "")[:DEFAULT_TAIL_BYTES]
        super().__init__(clean_reason)


def stop_process(process: subprocess.Popen[Any]) -> None:
    """Terminate one child process, escalating to kill after a short grace."""

    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2.0)


def bounded_log_tail(path: Path, *, maximum_bytes: int = DEFAULT_TAIL_BYTES) -> str:
    bound = max(0, int(maximum_bytes))
    if bound == 0:
        return ""
    try:
        with path.open("rb") as stream:
            stream.seek(max(0, path.stat().st_size - bound))
            return stream.read(bound).decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def run_external_process_sequence(
    commands: Sequence[tuple[str, Sequence[str]]],
    *,
    working_directory: str,
    environment: Mapping[str, str],
    timeout_seconds: int,
    cancelled: Callable[[], bool],
    log_name: Callable[[int], str] | None = None,
    stage_started: Callable[[int, int], None] | None = None,
    maximum_log_bytes: int | None = None,
    poll_seconds: float = DEFAULT_POLL_SECONDS,
) -> tuple[NativeExternalProcessStage, ...]:
    """Run an exact command sequence without a shell under one global timeout.

    Cancellation is cooperative through the host background-job manager. The
    command and environment are passed directly to ``Popen``; no command string
    is interpreted by a shell. Output is redirected to per-stage files so the
    in-memory Native result remains bounded.
    """

    exact_commands = tuple(
        (str(program), tuple(str(argument) for argument in arguments))
        for program, arguments in commands
    )
    if not exact_commands:
        raise ValueError("An external process sequence needs at least one command.")
    if not callable(cancelled):
        raise TypeError("cancelled must be callable")
    if stage_started is not None and not callable(stage_started):
        raise TypeError("stage_started must be callable")
    if type(timeout_seconds) is not int or timeout_seconds < 1:
        raise ValueError("timeout_seconds must be a positive integer")
    if maximum_log_bytes is not None and (
        type(maximum_log_bytes) is not int or maximum_log_bytes < 1
    ):
        raise ValueError("maximum_log_bytes must be a positive integer")
    if poll_seconds <= 0:
        raise ValueError("poll_seconds must be positive")

    root = Path(working_directory)
    if not root.is_dir():
        raise ValueError("working_directory must be an existing directory")
    make_log_name = log_name or (lambda stage: f"process-{stage}.log")
    started = time.monotonic()
    completed: list[NativeExternalProcessStage] = []

    for index, (program, arguments) in enumerate(exact_commands, start=1):
        if cancelled():
            raise NativeBackgroundCancelled()
        if stage_started is not None:
            stage_started(index, len(exact_commands))
        log_path = root / str(make_log_name(index))
        process: subprocess.Popen[Any] | None = None
        try:
            with log_path.open("wb") as log:
                process = subprocess.Popen(
                    [program, *arguments],
                    cwd=root,
                    env=dict(environment),
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    shell=False,
                )
                while process.poll() is None:
                    if cancelled():
                        stop_process(process)
                        raise NativeBackgroundCancelled()
                    if time.monotonic() - started > timeout_seconds:
                        stop_process(process)
                        raise NativeExternalProcessError(
                            "timeout",
                            stage=index,
                            program=program,
                        )
                    if (
                        maximum_log_bytes is not None
                        and log_path.stat().st_size > maximum_log_bytes
                    ):
                        stop_process(process)
                        raise NativeExternalProcessError(
                            "output_limit",
                            stage=index,
                            program=program,
                        )
                    time.sleep(poll_seconds)
                exit_code = int(process.returncode or 0)
        except (NativeBackgroundCancelled, NativeExternalProcessError):
            raise
        except Exception as exc:
            if process is not None:
                try:
                    stop_process(process)
                except Exception:
                    pass
            raise NativeExternalProcessError(
                "start_failed",
                stage=index,
                program=program,
            ) from exc

        if exit_code != 0:
            raise NativeExternalProcessError(
                "backend_failed",
                stage=index,
                program=program,
                exit_code=exit_code,
                detail=bounded_log_tail(log_path),
            )
        completed.append(
            NativeExternalProcessStage(
                stage=index,
                program=program,
                exit_code=exit_code,
                log_path=str(log_path),
            )
        )

    return tuple(completed)
