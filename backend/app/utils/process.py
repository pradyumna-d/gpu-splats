from __future__ import annotations

import asyncio
import os
import shlex
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from app.utils.logging import JobLogger

ProgressCallback = Callable[[int], Awaitable[None]]


class CommandError(RuntimeError):
    def __init__(self, command: list[str], returncode: int, log_path: Path) -> None:
        super().__init__(
            f"Command failed with exit code {returncode}: {' '.join(command)}. "
            f"See {log_path} for details."
        )
        self.command = command
        self.returncode = returncode
        self.log_path = log_path


class MissingCommandError(RuntimeError):
    def __init__(self, command: list[str], log_path: Path) -> None:
        executable = command[0] if command else "unknown"
        super().__init__(
            f"Required command not found: {executable}. Install it or make sure it is on PATH. "
            f"See {log_path} for details."
        )
        self.command = command
        self.executable = executable
        self.log_path = log_path


class ProcessRunner:
    def __init__(self, logger: JobLogger) -> None:
        self.logger = logger

    async def run(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        progress: ProgressCallback | None = None,
        progress_start: int | None = None,
        progress_end: int | None = None,
        estimated_seconds: float | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        started_at = time.monotonic()
        self.logger.info("command_started", command=command, cwd=str(cwd) if cwd else None)

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(cwd) if cwd else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env={**os.environ, **(env or {})},
            )
        except FileNotFoundError as exc:
            self.logger.error("command_not_found", command=command, executable=command[0])
            raise MissingCommandError(command, self.logger.log_path) from exc

        progress_task: asyncio.Task[None] | None = None
        if progress and progress_start is not None and progress_end is not None:
            progress_task = asyncio.create_task(
                self._tick_progress(progress, progress_start, progress_end, estimated_seconds)
            )

        assert process.stdout is not None
        async for raw_line in process.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            if line:
                self.logger.info("command_output", line=line)

        returncode = await process.wait()
        if progress_task:
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass

        duration = round(time.monotonic() - started_at, 3)
        self.logger.info("command_finished", command=command, exit_code=returncode, duration=duration)
        if returncode != 0:
            raise CommandError(command, returncode, self.logger.log_path)

        if progress and progress_end is not None:
            await progress(progress_end)

    async def _tick_progress(
        self,
        progress: ProgressCallback,
        start: int,
        end: int,
        estimated_seconds: float | None,
    ) -> None:
        estimate = max(estimated_seconds or 60.0, 1.0)
        began = time.monotonic()
        last_value = start
        await progress(start)
        while True:
            await asyncio.sleep(1)
            elapsed = time.monotonic() - began
            ratio = min(elapsed / estimate, 0.98)
            value = min(end - 1, max(start, int(start + (end - start) * ratio)))
            if value > last_value:
                last_value = value
                await progress(value)


def split_command(command_template: str, **values: Path | str | int) -> list[str]:
    formatted = command_template.format(**{key: str(value) for key, value in values.items()})
    return shlex.split(formatted)
