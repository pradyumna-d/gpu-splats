from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi import UploadFile

from app.events.bus import EventBus
from app.models.job import JobMetadata, JobStatus
from app.processing.video import VideoProcessor, VideoValidationError
from app.services.pipeline import VideoProcessorPipeline
from app.storage.manager import StorageManager
from app.utils.logging import JobLogger


class JobNotFoundError(KeyError):
    pass


class JobManager:
    def __init__(self, storage: StorageManager, events: EventBus) -> None:
        self.storage = storage
        self.events = events
        self.pipeline = VideoProcessorPipeline(storage)
        self.jobs: dict[str, JobMetadata] = {}
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.worker_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._last_emit: dict[str, float] = {}

    async def startup(self) -> None:
        for job in self.storage.load_all_metadata():
            if not job.is_terminal:
                job.status = JobStatus.FAILED
                job.error = "Application restarted before this job finished. Upload again to retry."
                job.updated_at = datetime.now(UTC)
                self.storage.save_metadata(job)
            self.jobs[job.job_id] = job
            await self._emit(job, force=True)
        self.worker_task = asyncio.create_task(self._worker_loop())

    async def shutdown(self) -> None:
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

    async def create_from_upload(self, upload: UploadFile) -> JobMetadata:
        if Path(upload.filename or "").suffix.lower() != ".mp4":
            raise VideoValidationError("Only MP4 uploads are supported.")

        job_id = self.storage.new_job_id()
        self.storage.create_job_workspace(job_id)
        try:
            video_path = await self.storage.save_upload(job_id, upload)
            logger = JobLogger(self.storage.job_log_path(job_id))
            await VideoProcessor(logger).validate_mp4(video_path)
        except Exception:
            self.storage.delete_job(job_id)
            raise

        job = JobMetadata(
            job_id=job_id,
            input_filename=upload.filename,
            video_path=str(video_path),
        )
        async with self._lock:
            self.jobs[job_id] = job
            self.storage.save_metadata(job)
        await self._emit(job, force=True)
        await self.queue.put(job_id)
        return job

    async def list_jobs(self) -> list[JobMetadata]:
        async with self._lock:
            return sorted(self.jobs.values(), key=lambda job: job.created_at, reverse=True)

    async def get_job(self, job_id: str) -> JobMetadata:
        async with self._lock:
            try:
                return self.jobs[job_id]
            except KeyError as exc:
                raise JobNotFoundError(job_id) from exc

    async def delete_job(self, job_id: str) -> None:
        async with self._lock:
            if job_id not in self.jobs:
                raise JobNotFoundError(job_id)
            del self.jobs[job_id]
            self.storage.delete_job(job_id)

    async def _worker_loop(self) -> None:
        while True:
            job_id = await self.queue.get()
            try:
                job = await self.get_job(job_id)
                await self.pipeline.run(job, lambda status, progress: self.update_job(job_id, status, progress))
                await self.complete_job(job_id)
            except Exception as exc:
                await self.fail_job(job_id, str(exc))
            finally:
                self.queue.task_done()

    async def update_job(self, job_id: str, status: JobStatus, progress: int) -> None:
        async with self._lock:
            job = self.jobs[job_id]
            job.status = status
            job.progress = max(0, min(progress, 100))
            job.updated_at = datetime.now(UTC)
            self.storage.save_metadata(job)
        await self._emit(job)

    async def complete_job(self, job_id: str) -> None:
        async with self._lock:
            job = self.jobs[job_id]
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.output_available = True
            job.output_path = str(self.storage.output_dir(job_id))
            job.viewer_url = f"/viewer/{job_id}"
            job.completed_at = datetime.now(UTC)
            job.updated_at = job.completed_at
            job.error = None
            self.storage.save_metadata(job)
        await self._emit(job, event="completed", force=True)

    async def fail_job(self, job_id: str, error: str) -> None:
        async with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return
            job.status = JobStatus.FAILED
            job.error = error
            job.updated_at = datetime.now(UTC)
            self.storage.save_metadata(job)
            JobLogger(self.storage.job_log_path(job_id)).error("job_failed", error=error)
        await self._emit(job, event="failed", force=True)

    async def _emit(self, job: JobMetadata, event: str = "status", force: bool = False) -> None:
        now = time.monotonic()
        last = self._last_emit.get(job.job_id, 0)
        if not force and event == "status" and now - last < 1:
            return
        self._last_emit[job.job_id] = now
        data = {
            "job_id": job.job_id,
            "status": job.status,
            "progress": job.progress,
        }
        if event == "completed":
            data["viewer_url"] = job.viewer_url
        if event == "failed":
            data["error"] = job.error
        await self.events.publish(job.job_id, event, data)
