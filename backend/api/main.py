"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text

from backend.api.dependencies import redis_client
from backend.api.routes.admin import router as admin_router
from backend.api.routes.auth import router as auth_router
from backend.api.routes.problems import router as problems_router
from backend.api.routes.submissions import router as submissions_router
from backend.common.config import settings
from backend.common.database import engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await redis_client.aclose()
    await engine.dispose()


app = FastAPI(
    title=settings.service_name,
    description="API for the ForgeJudge coding platform.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(problems_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(submissions_router)


@app.get("/health/live", tags=["health"])
async def liveness() -> dict[str, str]:
    """Report that the API process is alive."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def readiness() -> dict[str, str]:
    """Report readiness only when PostgreSQL and Redis are reachable."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        await redis_client.ping()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A required dependency is unavailable",
        ) from exc
    return {"status": "ready"}
