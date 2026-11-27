import json
import logging

from redis import Redis
from redis.exceptions import RedisError

from app.config import settings

log = logging.getLogger(__name__)


def channel(user_id: int) -> str:
    return f"jobmatch:user:{user_id}:events"


def publish(user_id: int, event: dict) -> None:
    try:
        with Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1) as client:
            client.publish(channel(user_id), json.dumps(event, ensure_ascii=False))
    except RedisError as exc:
        log.warning("не удалось опубликовать событие %s: %s", event["type"], exc)
