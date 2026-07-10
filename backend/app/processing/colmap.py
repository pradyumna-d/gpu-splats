from __future__ import annotations

import asyncio
import re
from pathlib import Path

from app.utils.config import Settings, settings
from app.utils.logging import JobLogger
from app.utils.process import ProcessRunner


class ColmapRunner:
    def __init__(self, logger: JobLogger, config: Settings = settings) -> None:
        self.logger = logger
        self.settings = config
        self.runner = ProcessRunner(logger)

    async def run(self, frames_dir: Path, colmap_dir: Path, progress) -> Path:
        frame_count = len(list(frames_dir.glob("*.jpg")))
        colmap_dir.mkdir(parents=True, exist_ok=True)
        sparse_dir = colmap_dir / "sparse"
        sparse_dir.mkdir(exist_ok=True)
        database_path = colmap_dir / "database.db"

        await self.runner.run(
            [
                "colmap",
                "feature_extractor",
                "--database_path",
                str(database_path),
                "--image_path",
                str(frames_dir),
                "--ImageReader.single_camera",
                "1",
                "--SiftExtraction.use_gpu",
                "1",
            ],
            progress=progress,
            progress_start=20,
            progress_end=32,
            estimated_seconds=120,
        )
        await self.runner.run(
            [
                "colmap",
                "sequential_matcher",
                "--database_path",
                str(database_path),
                "--SiftMatching.use_gpu",
                "1",
                "--SiftMatching.guided_matching",
                "1",
                "--SiftMatching.max_num_matches",
                "65536",
                "--SequentialMatching.overlap",
                "24",
            ],
            progress=progress,
            progress_start=32,
            progress_end=40,
            estimated_seconds=180,
        )
        await self.runner.run(
            [
                "colmap",
                "transitive_matcher",
                "--database_path",
                str(database_path),
                "--SiftMatching.use_gpu",
                "1",
                "--SiftMatching.guided_matching",
                "1",
            ],
            progress=progress,
            progress_start=40,
            progress_end=42,
            estimated_seconds=90,
        )
        await self.runner.run(
            [
                "colmap",
                "mapper",
                "--database_path",
                str(database_path),
                "--image_path",
                str(frames_dir),
                "--output_path",
                str(sparse_dir),
            ],
            progress=progress,
            progress_start=42,
            progress_end=50,
            estimated_seconds=240,
        )

        candidates = sorted(path for path in sparse_dir.iterdir() if path.is_dir())
        if not candidates:
            raise RuntimeError("COLMAP completed without producing a sparse model.")
        model_dir = await self._select_best_model(candidates)
        registered_images, points = await self._analyze_model(model_dir)
        registered_ratio = registered_images / frame_count if frame_count else 0
        self.logger.info(
            "colmap_model_selected",
            model_dir=str(model_dir),
            registered_images=registered_images,
            points=points,
            frame_count=frame_count,
            registered_ratio=registered_ratio,
        )
        if (
            registered_images < self.settings.colmap_min_registered_images
            or registered_ratio < self.settings.colmap_min_registered_ratio
        ):
            raise RuntimeError(
                "COLMAP only registered "
                f"{registered_images}/{frame_count} frames ({registered_ratio:.0%}). "
                "The capture is not connected enough for a reliable splat. "
                "Record one continuous slow orbit/walk around the room with strong overlap, "
                "avoid windows/mirrors/doorway transitions, and keep the phone upright."
            )
        return model_dir

    async def _select_best_model(self, candidates: list[Path]) -> Path:
        scored: list[tuple[int, int, Path]] = []
        for candidate in candidates:
            registered_images, points = await self._analyze_model(candidate)
            scored.append((registered_images, points, candidate))
            self.logger.info(
                "colmap_model_candidate",
                model_dir=str(candidate),
                registered_images=registered_images,
                points=points,
            )

        return max(scored, key=lambda score: (score[0], score[1], str(score[2])))[2]

    async def _analyze_model(self, model_dir: Path) -> tuple[int, int]:
        process = await asyncio.create_subprocess_exec(
            "colmap",
            "model_analyzer",
            "--path",
            str(model_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        assert process.stdout is not None
        output = ""
        async for raw_line in process.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            output += f"{line}\n"
            if line:
                self.logger.info("colmap_model_analyzer_output", model_dir=str(model_dir), line=line)
        returncode = await process.wait()
        if returncode != 0:
            return (0, 0)

        registered_match = re.search(r"Registered images:\s+(\d+)", output)
        points_match = re.search(r"Points:\s+(\d+)", output)
        registered_images = int(registered_match.group(1)) if registered_match else 0
        points = int(points_match.group(1)) if points_match else 0
        return (registered_images, points)
