"""Redis Streams consumer for submission jobs."""

import logging
from collections.abc import Mapping
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import ResponseError
from sqlalchemy.exc import SQLAlchemyError

from backend.common.config import settings
from backend.common.database import SessionFactory
from backend.repositories.submissions import SubmissionsRepository
from backend.worker.processor import process_submission

logger = logging.getLogger(__name__)


async def ensure_consumer_group(
    redis: Redis,
    *,
    stream: str | None = None,
    group: str | None = None,
) -> None:
    stream_name = stream or settings.submission_stream
    group_name = group or settings.submission_consumer_group
    try:
        await redis.xgroup_create(stream_name, group_name, id="0-0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def _handle_entry(
    redis: Redis,
    *,
    stream: str,
    group: str,
    message_id: str,
    fields: Mapping[str, str],
) -> bool:
    raw_submission_id = fields.get("submission_id")
    try:
        submission_id = UUID(raw_submission_id or "")
    except ValueError:
        logger.error("Discarding queue entry %s with an invalid submission id", message_id)
        await redis.xack(stream, group, message_id)
        return True

    try:
        await process_submission(submission_id)
    except Exception as exc:
        logger.exception("Submission %s processing failed", submission_id)
        try:
            async with SessionFactory() as session:
                await SubmissionsRepository().mark_failed(
                    session, submission_id, f"Worker processing failed: {exc}"
                )
                await session.commit()
        except SQLAlchemyError:
            logger.exception("Could not persist failure for submission %s", submission_id)
            return False

    await redis.xack(stream, group, message_id)
    return True


async def consume_once(
    redis: Redis,
    *,
    consumer: str,
    stream: str | None = None,
    group: str | None = None,
    block_ms: int = 1000,
) -> int:
    stream_name = stream or settings.submission_stream
    group_name = group or settings.submission_consumer_group
    entries = await redis.xreadgroup(
        group_name,
        consumer,
        {stream_name: ">"},
        count=10,
        block=block_ms,
    )
    processed = 0
    for _, messages in entries:
        for message_id, fields in messages:
            if await _handle_entry(
                redis,
                stream=stream_name,
                group=group_name,
                message_id=message_id,
                fields=fields,
            ):
                processed += 1
    return processed


async def reclaim_pending(
    redis: Redis,
    *,
    consumer: str,
    stream: str | None = None,
    group: str | None = None,
    min_idle_ms: int = 30_000,
) -> int:
    stream_name = stream or settings.submission_stream
    group_name = group or settings.submission_consumer_group
    _, messages, _ = await redis.xautoclaim(
        stream_name,
        group_name,
        consumer,
        min_idle_time=min_idle_ms,
        start_id="0-0",
        count=10,
    )
    processed = 0
    for message_id, fields in messages:
        if await _handle_entry(
            redis,
            stream=stream_name,
            group=group_name,
            message_id=message_id,
            fields=fields,
        ):
            processed += 1
    return processed
