import asyncio

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from redis.exceptions import RedisError

from app.config import settings
from app.db import SessionLocal
from app.deps import bearer, get_current_user
from app.events import channel

router = APIRouter(tags=["events"])


def stream_user_id(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> int:
    with SessionLocal() as db:
        return get_current_user(creds, db).id


@router.get("/events")
async def events(request: Request, user_id: int = Depends(stream_user_id)):
    async def stream():
        yield "retry: 3000\n\n"
        while not await request.is_disconnected():
            try:
                async with (
                    redis.from_url(settings.redis_url, socket_connect_timeout=2) as client,
                    client.pubsub() as pubsub,
                ):
                    await pubsub.subscribe(channel(user_id))
                    yield ": connected\n\n"
                    while not await request.is_disconnected():
                        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15)
                        yield f"data: {message['data'].decode()}\n\n" if message else ": ping\n\n"
            except RedisError:
                yield ": reconnecting\n\n"
                await asyncio.sleep(3)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
