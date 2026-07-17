from __future__ import annotations

from pathlib import Path

from app.utils.config import Settings, settings
from app.utils.logging import JobLogger
from app.utils.process import ProcessRunner, split_command


class SplatTrainer:
    def __init__(self, logger: JobLogger, config: Settings = settings) -> None:
        self.logger = logger
        self.settings = config
        self.runner = ProcessRunner(logger)

    async def train(self, dataset_dir: Path, training_dir: Path, progress) -> Path:
        training_dir.mkdir(parents=True, exist_ok=True)
        command_template = self.settings.splat_train_command or (
            "ns-train splatfacto "
            "--data {dataset_dir} "
            "--output-dir {training_dir} "
            "--vis tensorboard "
            "--max-num-iterations 30000 "
            "--pipeline.datamanager.cache-images cpu"
        )
        command = split_command(command_template, dataset_dir=dataset_dir, training_dir=training_dir)
        await self.runner.run(
            command,
            progress=progress,
            progress_start=55,
            progress_end=95,
            estimated_seconds=3600,
            env={"PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"},
        )

        configs = sorted(training_dir.rglob("config.yml"), key=lambda path: path.stat().st_mtime)
        if not configs:
            raise RuntimeError("Nerfstudio training completed without writing config.yml.")
        return configs[-1]

