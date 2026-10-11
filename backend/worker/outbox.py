"""Publish committed outbox events to the Redis submission stream."""

from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy import select

from backend.common.config import settings
from backend.common.database import SessionFactory
from backend.models import OutboxEvent


async def publish_pending(
    redis: Redis,
    *,
    batch_size: int = 100,
    stream: str | None = None,
) -> int:
    async with SessionFactory() as session:
        query = (
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.created_at, OutboxEvent.id)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        events = list((await session.scalars(query)).all())
        for event in events:
            fields = {key: str(value) for key, value in event.payload.items()}
            fields["event_type"] = event.event_type
            fields["outbox_event_id"] = str(event.id)
            await redis.xadd(stream or settings.submission_stream, fields)
            event.published_at = datetime.now(UTC)
        if events:
            await session.commit()
        return len(events)
