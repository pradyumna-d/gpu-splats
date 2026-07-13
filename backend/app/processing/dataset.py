from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from app.utils.logging import JobLogger
from app.utils.process import ProcessRunner


class DatasetPreparer:
    def __init__(self, logger: JobLogger) -> None:
        self.logger = logger
        self.runner = ProcessRunner(logger)

    def max_dimension(self, frame_count: int) -> int:
        if frame_count > 800:
            return 1024
        if frame_count > 500:
            return 1280
        return 1600

    async def prepare(self, frames_dir: Path, colmap_model_dir: Path, dataset_dir: Path, progress) -> Path:
        frame_paths = sorted(frames_dir.glob("*.jpg"))
        if not frame_paths:
            raise RuntimeError("No frames are available for dataset preparation.")
        if not colmap_model_dir.exists():
            raise RuntimeError("No COLMAP model is available for dataset preparation.")

        if dataset_dir.exists():
            shutil.rmtree(dataset_dir)
        dataset_dir.mkdir(parents=True, exist_ok=True)

        source_images_dir = dataset_dir.parent / "dataset_source_images"
        if source_images_dir.exists():
            shutil.rmtree(source_images_dir)
        source_images_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info("dataset_image_link_started", frames=len(frame_paths))

        for index, source in enumerate(frame_paths, start=1):
            target = source_images_dir / source.name
            if target.exists():
                target.unlink()
            try:
                os.link(source, target)
            except OSError:
                shutil.copy2(source, target)
            if index % 25 == 0 or index == len(frame_paths):
                value = 50 + int((index / len(frame_paths)) * 4)
                await progress(min(value, 54))

        await self.runner.run(
            [
                "ns-process-data",
                "images",
                "--data",
                str(source_images_dir),
                "--output-dir",
                str(dataset_dir),
                "--skip-colmap",
                "--colmap-model-path",
                str(colmap_model_dir),
            ],
            progress=progress,
            progress_start=54,
            progress_end=55,
            estimated_seconds=30,
        )
        self._remove_unregistered_images(dataset_dir)
        await progress(55)
        return dataset_dir

    def _remove_unregistered_images(self, dataset_dir: Path) -> None:
        transforms_path = dataset_dir / "transforms.json"
        images_dir = dataset_dir / "images"
        if not transforms_path.exists() or not images_dir.exists():
            return

        transforms = json.loads(transforms_path.read_text(encoding="utf-8"))
        referenced = {
            Path(frame["file_path"]).name
            for frame in transforms.get("frames", [])
            if isinstance(frame, dict) and frame.get("file_path")
        }
        if not referenced:
            return

        removed = 0
        for image_path in images_dir.glob("*.jpg"):
            if image_path.name not in referenced:
                image_path.unlink()
                removed += 1
        self.logger.info(
            "dataset_unregistered_images_removed",
            kept=len(referenced),
            removed=removed,
        )
