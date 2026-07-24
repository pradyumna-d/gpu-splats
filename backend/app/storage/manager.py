from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.models.job import JobMetadata
from app.utils.config import Settings, settings


class StorageManager:
    def __init__(self, config: Settings = settings) -> None:
        self.settings = config
        for path in (config.uploads_dir, config.jobs_dir, config.outputs_dir):
            path.mkdir(parents=True, exist_ok=True)

    def new_job_id(self) -> str:
        return str(uuid4())

    def job_dir(self, job_id: str) -> Path:
        return self.settings.jobs_dir / job_id

    def output_dir(self, job_id: str) -> Path:
        return self.settings.outputs_dir / job_id

    def metadata_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "metadata.json"

    def job_log_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "logs" / "job.log"

    def create_job_workspace(self, job_id: str) -> None:
        for relative in (
            "uploaded_video",
            "frames",
            "colmap",
            "dataset",
            "training",
            "export",
            "logs",
        ):
            (self.job_dir(job_id) / relative).mkdir(parents=True, exist_ok=True)
        self.output_dir(job_id).mkdir(parents=True, exist_ok=True)

    async def save_upload(self, job_id: str, upload: UploadFile) -> Path:
        extension = Path(upload.filename or "video.mp4").suffix.lower()
        destination = self.job_dir(job_id) / "uploaded_video" / f"source{extension}"
        with destination.open("wb") as handle:
            while chunk := await upload.read(self.settings.upload_chunk_size):
                handle.write(chunk)

        upload_link = self.settings.uploads_dir / f"{job_id}{extension}"
        if upload_link.exists() or upload_link.is_symlink():
            upload_link.unlink()
        try:
            os.symlink(destination, upload_link)
        except OSError:
            shutil.copy2(destination, upload_link)
        return destination

    def save_metadata(self, metadata: JobMetadata) -> None:
        path = self.metadata_path(metadata.job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(path)

    def load_metadata(self, job_id: str) -> JobMetadata:
        return JobMetadata.model_validate_json(self.metadata_path(job_id).read_text(encoding="utf-8"))

    def load_all_metadata(self) -> list[JobMetadata]:
        jobs: list[JobMetadata] = []
        for path in sorted(self.settings.jobs_dir.glob("*/metadata.json")):
            try:
                jobs.append(JobMetadata.model_validate_json(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, ValueError):
                continue
        return sorted(jobs, key=lambda job: job.created_at, reverse=True)

    def delete_job(self, job_id: str) -> None:
        shutil.rmtree(self.job_dir(job_id), ignore_errors=True)
        shutil.rmtree(self.output_dir(job_id), ignore_errors=True)
        for upload in self.settings.uploads_dir.glob(f"{job_id}.*"):
            upload.unlink(missing_ok=True)

