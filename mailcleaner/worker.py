import json
import logging
import threading

from redis.exceptions import RedisError

from mailcleaner.config import get_request_queue
from mailcleaner.redis_client import get_redis_client
from mailcleaner.services.jobs import process_raw_job

logger = logging.getLogger("mailcleaner")


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
