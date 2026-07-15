from __future__ import annotations

import asyncio
import re
from pathlib import Path

from app.utils.config import Settings, settings
from app.utils.logging import JobLogger


class FrameExtractor:
    def __init__(self, logger: JobLogger, config: Settings = settings) -> None:
        self.logger = logger
        self.settings = config

    def choose_fps(self, duration_seconds: float) -> float:
        if duration_seconds <= 180:
            fps = 4.0
        elif duration_seconds <= 300:
            fps = 2.0
        else:
            fps = 1.0
        estimated = duration_seconds * fps
        if estimated > self.settings.max_frames:
            fps = self.settings.max_frames / duration_seconds
        return max(fps, 0.05)

    def estimate_frame_count(self, duration_seconds: float, fps: float) -> int:
        return max(1, min(self.settings.max_frames, int(duration_seconds * fps)))

    def max_dimension(self, estimated_frame_count: int) -> int:
        if estimated_frame_count > 800:
            return 1024
        if estimated_frame_count > 500:
            return 1280
        return 1600

    async def extract(
        self,
        video_path: Path,
        frames_dir: Path,
        duration_seconds: float,
        progress,
    ) -> int:
        frames_dir.mkdir(parents=True, exist_ok=True)
        fps = self.choose_fps(duration_seconds)
        estimated_frames = self.estimate_frame_count(duration_seconds, fps)
        max_dim = self.max_dimension(estimated_frames)
        output_pattern = frames_dir / "%06d.jpg"
        filters = (
            f"fps={fps:.6f},"
            f"scale='if(gte(iw,ih),min({max_dim},iw),-2)':"
            f"'if(gte(iw,ih),-2,min({max_dim},ih))'"
        )
        command = [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            filters,
            "-q:v",
            "2",
            "-progress",
            "pipe:1",
            "-nostats",
            str(output_pattern),
        ]
        self.logger.info(
            "frame_extraction_started",
            command=command,
            fps=fps,
            estimated_frames=estimated_frames,
            max_dimension=max_dim,
        )
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        assert process.stdout is not None
        last_progress = 0
        time_re = re.compile(r"out_time_ms=(\d+)")
        async for raw_line in process.stdout:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if line:
                self.logger.info("ffmpeg_output", line=line)
            match = time_re.search(line)
            if match:
                elapsed = int(match.group(1)) / 1_000_000
                value = min(19, int((elapsed / duration_seconds) * 20))
                if value > last_progress:
                    last_progress = value
                    await progress(value)

        returncode = await process.wait()
        if returncode != 0:
            raise RuntimeError("FFmpeg frame extraction failed. See job log for details.")

        frame_count = len(list(frames_dir.glob("*.jpg")))
        if frame_count == 0:
            raise RuntimeError("FFmpeg did not extract any frames.")
        self.logger.info("frame_extraction_finished", frames=frame_count)
        await progress(20)
        return frame_count
