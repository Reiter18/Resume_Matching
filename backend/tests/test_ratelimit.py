import fakeredis
import pytest
from fastapi.testclient import TestClient
from redis import Redis

from app.main import app
from app.ratelimit import LoginLimiter, RateLimited
from tests.test_auth import register

IP, EMAIL = "10.0.0.1", "user@example.com"


def make_limiter(**kw):
    args = dict(max_attempts=3, ip_max_attempts=5, window_seconds=900) | kw
    return LoginLimiter(fakeredis.FakeRedis(server=fakeredis.FakeServer()), **args)


def test_blocks_after_max_failures_per_ip_and_email():
    lim = make_limiter()
    for _ in range(3):
        lim.check(IP, EMAIL)
        lim.failure(IP, "User@Example.com")  
    with pytest.raises(RateLimited) as e:
        lim.check(IP, " user@example.com ")
    assert 1 <= e.value.retry_after <= 900
    lim.check(IP, "other@example.com")  
    lim.check("10.0.0.2", EMAIL)  


def test_success_resets_pair_but_ip_counter_stays():
    lim = make_limiter()
    lim.failure(IP, EMAIL)
    lim.failure(IP, EMAIL)
    lim.success(IP, EMAIL)
    lim.check(IP, EMAIL)  
    assert 0 < lim.redis.ttl(f"login_fail_ip:{IP}") <= 900  
    for i in range(5):  
        lim.failure(IP, f"user{i}@example.com")
    with pytest.raises(RateLimited):
        lim.check(IP, "brand-new@example.com")


def test_redis_down_means_no_blocking():
    lim = LoginLimiter(Redis.from_url("redis://localhost:1/0", socket_connect_timeout=0.2), 3, 5, 900)
    for _ in range(10):
        lim.failure(IP, EMAIL)  
        lim.check(IP, EMAIL)  


@pytest.fixture()
def client(db):
    return TestClient(app)


def login(client, password, email=EMAIL):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_login_blocked_after_five_failures(client):
    register(client)
    for _ in range(5):
        assert login(client, "wrong-password").status_code == 401
    blocked = login(client, "wrong-password")
    assert blocked.status_code == 429 and int(blocked.headers["Retry-After"]) > 0
    assert "Повторите через" in blocked.json()["detail"]
    assert login(client, "correct-horse-1").status_code == 429  
    assert login(client, "whatever-123", "someone-else@example.com").status_code == 401  


def test_successful_login_resets_failures(client):
    register(client)
    for _ in range(4):
        login(client, "wrong-password")
    assert login(client, "correct-horse-1").status_code == 200
    for _ in range(4):  
        assert login(client, "wrong-password").status_code == 401
