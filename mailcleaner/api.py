from fastapi import APIRouter, HTTPException, Request
from redis.exceptions import RedisError

from mailcleaner.config import get_request_queue
from mailcleaner.schemas import CleanerJob, QueuedJobResponse
from mailcleaner.services.jobs import serialize_job

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    try:
        request.app.state.redis.ping()
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis is unavailable") from exc

    return {"status": "ok"}


@router.post("/jobs", response_model=QueuedJobResponse, status_code=202)
def create_job(request: Request, job: CleanerJob) -> QueuedJobResponse:
    try:
        request.app.state.redis.rpush(get_request_queue(), serialize_job(job))
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis is unavailable") from exc

    return QueuedJobResponse(jobId=job.jobId, status="queued")
