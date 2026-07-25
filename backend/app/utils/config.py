from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GSPLAT_", env_file=".env", extra="ignore")

    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data"
    uploads_dir: Path = PROJECT_ROOT / "data" / "uploads"
    jobs_dir: Path = PROJECT_ROOT / "data" / "jobs"
    outputs_dir: Path = PROJECT_ROOT / "data" / "outputs"

    upload_chunk_size: int = 1024 * 1024
    max_frames: int = 800
    frame_log_interval_seconds: float = 1.0
    colmap_min_registered_ratio: float = 0.55
    colmap_min_registered_images: int = 80
    splat_train_command: str | None = None
    splat_export_command: str | None = None


settings = Settings()
