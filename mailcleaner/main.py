import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from mailcleaner.api import router
from mailcleaner.config import configure_logging, get_env_bool
from mailcleaner.redis_client import get_redis_client
from mailcleaner.worker import worker_loop

configure_logging()


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


def create_app() -> FastAPI:
    app_instance = FastAPI(
        title="MDK Mail Cleaner API",
        version="2.0.0",
        lifespan=lifespan,
    )
    app_instance.include_router(router)
    return app_instance


app = create_app()
