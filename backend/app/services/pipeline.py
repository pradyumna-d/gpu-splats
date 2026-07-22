from __future__ import annotations

from app.models.job import JobMetadata, JobStatus
from app.processing.colmap import ColmapRunner
from app.processing.dataset import DatasetPreparer
from app.processing.exporter import SplatExporter
from app.processing.frames import FrameExtractor
from app.processing.trainer import SplatTrainer
from app.processing.video import VideoProcessor
from app.storage.manager import StorageManager
from app.utils.logging import JobLogger


class VideoProcessorPipeline:
    def __init__(self, storage: StorageManager) -> None:
        self.storage = storage

    async def run(self, job: JobMetadata, update) -> None:
        if not job.video_file:
            raise RuntimeError("Job does not have an uploaded video.")

        logger = JobLogger(self.storage.job_log_path(job.job_id))
        video = VideoProcessor(logger)
        frames = FrameExtractor(logger)
        colmap = ColmapRunner(logger)
        dataset = DatasetPreparer(logger)
        trainer = SplatTrainer(logger)
        exporter = SplatExporter(logger)

        workspace = self.storage.job_dir(job.job_id)
        output_dir = self.storage.output_dir(job.job_id)

        probe = await video.validate_mp4(job.video_file)
        await update(JobStatus.EXTRACTING_FRAMES, 0)
        frame_count = await frames.extract(
            job.video_file,
            workspace / "frames",
            float(probe["duration"]),
            lambda value: update(JobStatus.EXTRACTING_FRAMES, value),
        )

        await update(JobStatus.RUNNING_COLMAP, 20)
        colmap_model = await colmap.run(
            workspace / "frames",
            workspace / "colmap",
            lambda value: update(JobStatus.RUNNING_COLMAP, value),
        )

        await update(JobStatus.PREPARING_DATASET, 50)
        dataset_dir = await dataset.prepare(
            workspace / "frames",
            colmap_model,
            workspace / "dataset",
            lambda value: update(JobStatus.PREPARING_DATASET, value),
        )

        logger.info("dataset_prepared", frame_count=frame_count, dataset_dir=str(dataset_dir))
        await update(JobStatus.TRAINING, 55)
        config_path = await trainer.train(
            dataset_dir,
            workspace / "training",
            lambda value: update(JobStatus.TRAINING, value),
        )

        await update(JobStatus.EXPORTING, 95)
        await exporter.export(
            config_path,
            workspace / "export",
            output_dir,
            lambda value: update(JobStatus.EXPORTING, value),
        )

