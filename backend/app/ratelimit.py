import logging
from typing import Optional

from redis import Redis
from redis.exceptions import RedisError

from app.config import settings

log = logging.getLogger(__name__)


class RateLimited(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = max(retry_after, 1)


class LoginLimiter:
    def __init__(self, redis: Redis, max_attempts: int, ip_max_attempts: int, window_seconds: int):
        self.redis = redis
        self.max_attempts = max_attempts
        self.ip_max_attempts = ip_max_attempts
        self.window = window_seconds

    @staticmethod
    def _keys(ip: str, email: str) -> tuple[str, str]:
        return f"login_fail:{ip}:{email.strip().lower()}", f"login_fail_ip:{ip}"

    def check(self, ip: str, email: str) -> None:
        pair_key, ip_key = self._keys(ip, email)
        try:
            for key, limit in ((pair_key, self.max_attempts), (ip_key, self.ip_max_attempts)):
                count = int(self.redis.get(key) or 0)
                if count >= limit:
                    raise RateLimited(self.redis.ttl(key))
        except RedisError as e:
            log.warning("Redis недоступен, лимит входа не проверяется: %s", e)

    def failure(self, ip: str, email: str) -> None:
        try:
            for key in self._keys(ip, email):
                if self.redis.incr(key) == 1:
                    self.redis.expire(key, self.window)
        except RedisError as e:
            log.warning("Redis недоступен, неудачный вход не записан: %s", e)

    def success(self, ip: str, email: str) -> None:
        try:
            self.redis.delete(self._keys(ip, email)[0])  
        except RedisError as e:
            log.warning("Redis недоступен: %s", e)


_limiter: Optional[LoginLimiter] = None


def get_login_limiter() -> LoginLimiter:
    global _limiter
    if _limiter is None:
        client = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        _limiter = LoginLimiter(
            client, settings.login_max_attempts, settings.login_ip_max_attempts, settings.login_window_seconds
        )
    return _limiter
