import base64
import binascii
import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from typing import Any

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from redis import Redis
from redis.exceptions import RedisError

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("mailcleaner")


class EmailPayload(BaseModel):
    emailId: str = Field(..., min_length=1)
    folderId: str = Field(..., min_length=1)
    base64Content: str = Field(..., min_length=1)


class CleanerJob(BaseModel):
    jobId: str = Field(..., min_length=1)
    resultQueue: str = Field(..., min_length=1)
    payload: EmailPayload


class QueuedJobResponse(BaseModel):
    jobId: str
    status: str


def get_env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def get_request_queue() -> str:
    return os.getenv("REQUEST_QUEUE", "mailcleaner:requests")


def get_redis_client() -> Redis:
    password = os.getenv("REDIS_PW", "password")
    if password == "":
        password = None

    return Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=password,
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
    )


def encode_base64(text: str) -> str:
    encoded_bytes = base64.b64encode(text.encode("utf-8"))
    return encoded_bytes.decode("utf-8")


def decode_base64(encoded_text: str) -> str:
    try:
        decoded_bytes = base64.b64decode(encoded_text, validate=True)
        return decoded_bytes.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise ValueError("invalid base64 content") from exc


def extract_readable_text(base64_html_content: str) -> str:
    decoded_content = decode_base64(base64_html_content)
    soup = BeautifulSoup(decoded_content, "html.parser")

    for tag in soup(["script", "style", "head", "noscript"]):
        tag.decompose()

    clean_content = soup.get_text(separator=" ", strip=True)
    if not clean_content:
        raise ValueError("empty cleaned content")

    return clean_content


def build_success_result(job: CleanerJob, clean_content: str) -> dict[str, Any]:
    return {
        "jobId": job.jobId,
        "status": "success",
        "emailId": job.payload.emailId,
        "folderId": job.payload.folderId,
        "base64Content": encode_base64(clean_content),
    }


def build_error_result(
    job_id: str,
    result_queue: str | None,
    email_id: str | None,
    folder_id: str | None,
    error_code: str,
    message: str,
) -> tuple[str | None, dict[str, Any]]:
    return result_queue, {
        "jobId": job_id,
        "status": "error",
        "emailId": email_id,
        "folderId": folder_id,
        "errorCode": error_code,
        "message": message,
    }


def parse_job(raw_job: bytes | str) -> CleanerJob:
    try:
        data = json.loads(raw_job)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON job") from exc

    return CleanerJob.model_validate(data)


def serialize_job(job: CleanerJob) -> str:
    return job.model_dump_json()


def process_raw_job(raw_job: bytes | str) -> tuple[str | None, dict[str, Any]]:
    try:
        raw_data = json.loads(raw_job)
    except json.JSONDecodeError:
        return build_error_result(
            "unknown",
            None,
            None,
            None,
            "invalid_payload",
            "Job is not valid JSON",
        )

    job_id = raw_data.get("jobId", "unknown")
    result_queue = raw_data.get("resultQueue")
    payload = raw_data.get("payload") or {}
    email_id = payload.get("emailId")
    folder_id = payload.get("folderId")

    try:
        job = parse_job(raw_job)
    except ValueError as exc:
        return build_error_result(
            str(job_id),
            result_queue,
            email_id,
            folder_id,
            "invalid_payload",
            str(exc),
        )

    try:
        clean_content = extract_readable_text(job.payload.base64Content)
        return job.resultQueue, build_success_result(job, clean_content)
    except ValueError as exc:
        return build_error_result(
            job.jobId,
            job.resultQueue,
            job.payload.emailId,
            job.payload.folderId,
            "invalid_base64",
            str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected error processing job %s", job.jobId)
        return build_error_result(
            job.jobId,
            job.resultQueue,
            job.payload.emailId,
            job.payload.folderId,
            "processing_error",
            str(exc),
        )


def worker_loop(stop_event: threading.Event) -> None:
    request_queue = get_request_queue()
    redis_client = get_redis_client()
    logger.info("Starting worker on queue %s", request_queue)

    while not stop_event.is_set():
        try:
            item = redis_client.blpop(request_queue, timeout=1)
            if not item:
                continue

            _, raw_job = item
            result_queue, result = process_raw_job(raw_job)
            if not result_queue:
                logger.error("Unable to publish job result without resultQueue: %s", result)
                continue

            redis_client.rpush(result_queue, json.dumps(result))
            logger.info("Published job %s result to %s", result.get("jobId"), result_queue)
        except RedisError:
            logger.exception("Redis error in worker loop")
            stop_event.wait(2)
        except Exception:
            logger.exception("Unexpected worker error")
            stop_event.wait(2)

    logger.info("Worker stopped")


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    stop_event = threading.Event()
    worker_enabled = get_env_bool("WORKER_ENABLED", True)
    worker_thread = None

    app_instance.state.redis = get_redis_client()
    app_instance.state.stop_event = stop_event

    if worker_enabled:
        worker_thread = threading.Thread(target=worker_loop, args=(stop_event,), daemon=True)
        worker_thread.start()

    try:
        yield
    finally:
        stop_event.set()
        if worker_thread:
            worker_thread.join(timeout=5)
        app_instance.state.redis.close()


app = FastAPI(
    title="MDK Mail Cleaner API",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    try:
        app.state.redis.ping()
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis is unavailable") from exc

    return {"status": "ok"}


@app.post("/jobs", response_model=QueuedJobResponse, status_code=202)
def create_job(job: CleanerJob) -> QueuedJobResponse:
    try:
        app.state.redis.rpush(get_request_queue(), serialize_job(job))
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis is unavailable") from exc

    return QueuedJobResponse(jobId=job.jobId, status="queued")
