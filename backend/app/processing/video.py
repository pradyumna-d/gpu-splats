from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.utils.logging import JobLogger


class VideoValidationError(ValueError):
    pass


class VideoProcessor:
    def __init__(self, logger: JobLogger) -> None:
        self.logger = logger

    async def validate_mp4(self, path: Path) -> dict[str, float | int | str]:
        if path.suffix.lower() != ".mp4":
            raise VideoValidationError("Only MP4 uploads are supported.")
        if path.stat().st_size == 0:
            raise VideoValidationError("Uploaded file is empty.")

        command = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_type,width,height,duration",
            "-of",
            "json",
            str(path),
        ]
        self.logger.info("video_probe_started", command=command)
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            self.logger.error("video_probe_failed", stderr=stderr.decode("utf-8", errors="replace"))
            raise VideoValidationError("The MP4 file could not be read by ffprobe.")

        data = json.loads(stdout.decode("utf-8"))
        streams = data.get("streams") or []
        if not streams:
            raise VideoValidationError("The MP4 file does not contain a video stream.")

        stream = streams[0]
        duration = float(stream.get("duration") or 0)
        if duration <= 0:
            raise VideoValidationError("The MP4 file has no readable duration.")

        metadata = {
            "duration": duration,
            "width": int(stream.get("width") or 0),
            "height": int(stream.get("height") or 0),
        }
        self.logger.info("video_probe_finished", **metadata)
        return metadata

