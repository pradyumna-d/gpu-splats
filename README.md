# Gaussian Splats Workstation

A local-first FastAPI + React application for converting uploaded MP4 videos into browser-viewable Gaussian Splat reconstructions on a single Ubuntu workstation.

```text
MP4 upload -> frame extraction -> COLMAP -> Nerfstudio Splatfacto -> scene output -> browser viewer
```

## Architecture

- `backend/`: FastAPI API, persisted job manager, SSE event bus, and disk-backed processing services.
- `frontend/`: React/Vite UI with upload, job history, and Three.js Gaussian Splat viewer.
- `data/uploads/`: uploaded MP4 staging links.
- `data/jobs/<job_id>/`: job workspace, frames, COLMAP data, training artifacts, logs, and `metadata.json`.
- `data/outputs/<job_id>/`: exported scene file, `thumbnail.jpg`, and output metadata.

The backend runs one local async worker by default. Jobs survive API restarts as persisted metadata; in-flight jobs are marked failed on restart so they do not remain stuck as zombies.

## Requirements

- Ubuntu 24.04
- Python 3.12 for the project venv
- Node.js 20+
- FFmpeg and ffprobe
- COLMAP
- CUDA-capable NVIDIA GPU
- Nerfstudio with Splatfacto installed in the backend environment

Target memory behavior is conservative: frames are streamed to disk, frame count is capped at 800, and training uses Nerfstudio with CPU image caching by default.

## Installation

```bash
./scripts/install_system_dependencies.sh
```

The installer creates `backend/.venv` and installs backend Python dependencies there. By default it also installs PyTorch CUDA wheels and Nerfstudio into that same venv, so the host Python environment is not modified.

The only host-level packages are workstation tools installed by apt, such as FFmpeg and COLMAP. Those are command-line system binaries, not Python packages.

The default PyTorch wheel index is CUDA 12.8:

```bash
GSPLAT_TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128 ./scripts/install_system_dependencies.sh
```

To skip the large Nerfstudio/PyTorch install and only install the backend API dependencies:

```bash
GSPLAT_INSTALL_NERFSTUDIO=0 ./scripts/install_system_dependencies.sh
```

The default pipeline expects these commands in `backend/.venv/bin`:

```bash
ns-process-data
ns-train
ns-export
```

If your Nerfstudio version needs different flags, override the generated commands:

```bash
export GSPLAT_SPLAT_TRAIN_COMMAND='ns-train splatfacto --data {dataset_dir} --output-dir {training_dir}'
export GSPLAT_SPLAT_EXPORT_COMMAND='ns-export gaussian-splat --load-config {config_path} --output-dir {export_dir}'
```

## CUDA Verification

```bash
./scripts/check_environment.sh
```

Confirm that `nvidia-smi` shows the RTX GPU and that PyTorch reports CUDA availability from the same environment used to start the backend.

## Startup

Backend:

```bash
./scripts/start_backend.sh
```

`start_backend.sh` automatically prepends `backend/.venv/bin` to `PATH`, so worker subprocesses can find `ns-process-data`, `ns-train`, and `ns-export` installed inside the venv.

Frontend:

```bash
./scripts/start_frontend.sh
```

Open:

```text
http://localhost:5173
```

## API

- `POST /api/upload`: multipart upload with field `video`; accepts `.mp4`.
- `GET /api/jobs`: list persisted jobs.
- `GET /api/jobs/{job_id}`: job metadata.
- `DELETE /api/jobs/{job_id}`: remove upload, workspace, and output.
- `GET /api/jobs/{job_id}/events`: Server-Sent Events for `status`, `completed`, and `failed`.

The frontend uses native `EventSource`; there is no status polling.

## Processing Notes

- Frame extraction uses FFmpeg and never loads video into Python memory.
- Extraction is adaptive: 2 FPS for videos up to 3 minutes, 1 FPS for 3-5 minutes, and 0.5 FPS after 5 minutes.
- If the estimated frame count exceeds 800, extraction FPS is automatically reduced.
- Images are resized on disk before training: 1600 px max dimension up to 500 frames, 1280 px above 500 frames, and 1024 px above 800 frames.
- COLMAP stdout/stderr and every command are written as structured JSON lines to `data/jobs/<job_id>/logs/job.log`.

## Docker

`docker-compose.yml` is provided for local development only:

```bash
docker compose up
```

GPU and Nerfstudio availability inside Docker depend on NVIDIA Container Toolkit and a CUDA-compatible image. For production reconstruction on the target workstation, running directly in the host Python environment is simpler.

## Troubleshooting

- Upload rejected: ensure the file extension is `.mp4` and `ffprobe` can read a video stream.
- COLMAP fails early: check GPU visibility, image count, and `data/jobs/<job_id>/logs/job.log`.
- Training exits without `config.yml`: verify the installed Nerfstudio CLI matches `GSPLAT_SPLAT_TRAIN_COMMAND`.
- Export creates only `.ply`: `@mkkellogg/gaussian-splats-3d` can load common Gaussian Splat formats. The app preserves the exported scene extension and records the file in output metadata.
- Browser viewer is blank: check `data/outputs/<job_id>/metadata.json`, the referenced scene file, browser console errors, and whether the exported format is supported by the viewer package.
