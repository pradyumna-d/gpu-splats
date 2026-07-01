from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import StreamingResponse

from app.jobs.manager import JobManager, JobNotFoundError
from app.processing.video import VideoValidationError

router = APIRouter(prefix="/api")


def get_job_manager(request: Request) -> JobManager:
    return request.app.state.job_manager


@router.post("/upload")
async def upload_video(
    video: UploadFile = File(...),
    jobs: JobManager = Depends(get_job_manager),
) -> dict[str, str]:
    try:
        job = await jobs.create_from_upload(video)
    except VideoValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job_id": job.job_id}


@router.get("/jobs")
async def list_jobs(jobs: JobManager = Depends(get_job_manager)) -> list[dict]:
    return [job.public_dict() for job in await jobs.list_jobs()]


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, jobs: JobManager = Depends(get_job_manager)) -> dict:
    try:
        return (await jobs.get_job(job_id)).public_dict()
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


@router.delete("/jobs/{job_id}", status_code=204, response_class=Response)
async def delete_job(job_id: str, jobs: JobManager = Depends(get_job_manager)) -> Response:
    try:
        await jobs.delete_job(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return Response(status_code=204)


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str, jobs: JobManager = Depends(get_job_manager)) -> StreamingResponse:
    try:
        await jobs.get_job(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    return StreamingResponse(
        jobs.events.stream(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
