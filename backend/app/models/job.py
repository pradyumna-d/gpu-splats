from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    QUEUED = "queued"
    EXTRACTING_FRAMES = "extracting_frames"
    RUNNING_COLMAP = "running_colmap"
    PREPARING_DATASET = "preparing_dataset"
    TRAINING = "training"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"


TERMINAL_STATUSES = {JobStatus.COMPLETED, JobStatus.FAILED}


def now_utc() -> datetime:
    return datetime.now(UTC)


class JobMetadata(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    progress: int = Field(default=0, ge=0, le=100)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    completed_at: datetime | None = None
    output_available: bool = False
    input_filename: str | None = None
    video_path: str | None = None
    output_path: str | None = None
    viewer_url: str | None = None
    error: str | None = None

    def public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data.pop("video_path", None)
        data.pop("output_path", None)
        return data

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    @property
    def video_file(self) -> Path | None:
        return Path(self.video_path) if self.video_path else None

