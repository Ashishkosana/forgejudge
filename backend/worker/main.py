"""Graceful worker process entry point."""

import asyncio
import logging
import signal

from backend.common.config import settings
from backend.common.redis import create_redis_client
from backend.worker.consumer import consume_once, ensure_consumer_group, reclaim_pending
from backend.worker.outbox import publish_pending


async def run() -> None:
    """Consume queued submission IDs until the container runtime stops the worker."""
    logging.basicConfig(level=settings.log_level.upper())
    logger = logging.getLogger(__name__)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()

    for stop_signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(stop_signal, stop.set)

    redis = create_redis_client()
    try:
        await ensure_consumer_group(redis)
        logger.info("Worker consuming stream %s", settings.submission_stream)
        while not stop.is_set():
            try:
                await publish_pending(redis)
                await reclaim_pending(redis, consumer=settings.worker_consumer_name)
                await consume_once(redis, consumer=settings.worker_consumer_name, block_ms=1000)
            except Exception:
                logger.exception("Worker queue poll failed")
                try:
                    await asyncio.wait_for(stop.wait(), timeout=1)
                except TimeoutError:
                    pass
    finally:
        await redis.aclose()
        logger.info("Worker process stopped")


if __name__ == "__main__":
    asyncio.run(run())
