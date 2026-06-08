import json
import logging
from typing import Any

from mailcleaner.schemas import CleanerJob
from mailcleaner.services.cleaner import extract_readable_text
from mailcleaner.services.encoding import encode_base64

logger = logging.getLogger("mailcleaner")


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
