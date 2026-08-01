# Pipeline Details

Each job is processed in these persisted stages:

1. `queued`
2. `extracting_frames` from 0-20%
3. `running_colmap` from 20-50%
4. `preparing_dataset` from 50-55%
5. `training` from 55-95%
6. `exporting` from 95-100%
7. `completed` or `failed`

The `JobManager` owns state transitions, writes `metadata.json`, and publishes SSE messages through `EventBus`. Services do not store job state directly; they receive progress callbacks and write detailed command logs.

Long-running commands are executed with stdout and stderr streamed into `data/jobs/<job_id>/logs/job.log`. The application prefers marking a job failed with logs over retrying blindly, because reconstruction failures are usually data, environment, or GPU-memory specific.

