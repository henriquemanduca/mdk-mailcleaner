import os

from redis import Redis


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
