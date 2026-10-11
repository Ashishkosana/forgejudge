"""API-to-Redis-to-worker integration coverage; requires Compose dependencies."""

import os
from uuid import UUID, uuid4

import pytest
from backend.api.dependencies import get_current_user
from backend.api.main import app
from backend.common.config import settings
from backend.common.database import SessionFactory
from backend.common.redis import create_redis_client
from backend.models import OutboxEvent, Problem, Submission, User
from backend.models import TestCase as CaseModel
from backend.models.enums import SubmissionVerdict
from backend.models.judging import ExecutionResult
from backend.worker.consumer import consume_once, ensure_consumer_group
from backend.worker.outbox import publish_pending
from backend.worker.processor import process_submission
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete


class IntegrationRunner:
    def execute(
        self,
        source_code: str,
        input_data: str,
        *,
        time_limit_ms: int,
        memory_limit_mb: int,
    ) -> ExecutionResult:
        del source_code, time_limit_ms, memory_limit_mb
        output = "7\n" if input_data == "2 5\n" else "2\n"
        return ExecutionResult(SubmissionVerdict.ACCEPTED, 1.0, 1024, output, "")


@pytest.mark.integration
async def test_problem_submission_outbox_and_worker_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.environ.get("FORGEJUDGE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set FORGEJUDGE_TEST_DATABASE_URL to run PostgreSQL integration tests")
    if database_url != settings.database_url:
        pytest.skip(
            "Set DATABASE_URL to FORGEJUDGE_TEST_DATABASE_URL for PostgreSQL integration tests"
        )

    problem_slug = f"integration-{uuid4().hex}"
    stream = f"forgejudge:test:{uuid4().hex}"
    group = f"workers:{uuid4().hex}"
    redis = create_redis_client()
    submission_id: UUID | None = None
    user_id: UUID | None = None

    async with SessionFactory() as session:
        user = User(
            email=f"integration-{uuid4().hex}@example.test",
            display_name="Integration User",
            role="user",
        )
        session.add(user)
        await session.flush()
        user_id = user.id
        await session.commit()
    monkeypatch.setitem(app.dependency_overrides, get_current_user, lambda: user)

    async def process_with_test_runner(submission_id: UUID) -> bool:
        return await process_submission(submission_id, runner=IntegrationRunner())

    monkeypatch.setattr(
        "backend.worker.consumer.process_submission",
        process_with_test_runner,
    )

    async with SessionFactory() as session:
        problem = Problem(
            slug=problem_slug,
            title="Integration Addition",
            description="Print the sum of the two integers.",
            difficulty="easy",
            is_published=True,
        )
        session.add(problem)
        await session.flush()
        session.add_all(
            [
                CaseModel(
                    problem_id=problem.id,
                    position=0,
                    input_data="2 5\n",
                    expected_output="7\n",
                    is_sample=True,
                ),
                CaseModel(
                    problem_id=problem.id,
                    position=1,
                    input_data="-2 4\n",
                    expected_output="2\n",
                    is_sample=False,
                ),
            ]
        )
        await session.commit()
        problem_id = problem.id

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://forgejudge.test"
        ) as client:
            problem_list = await client.get("/problems")
            assert problem_list.status_code == 200
            assert problem_list.json()["total"] >= 1

            problem_detail = await client.get(f"/problems/{problem_id}")
            assert problem_detail.status_code == 200
            assert len(problem_detail.json()["sample_test_cases"]) == 1

            created = await client.post(
                "/submissions",
                json={
                    "problem_id": str(problem_id),
                    "language": "python",
                    "source_code": "a, b = map(int, input().split())\nprint(a + b)",
                },
            )
            assert created.status_code == 202
            submission_id = UUID(created.json()["id"])
            assert created.json()["status"] == "QUEUED"

            assert await publish_pending(redis, stream=stream) == 1
            await ensure_consumer_group(redis, stream=stream, group=group)
            assert (
                await consume_once(
                    redis,
                    consumer="integration-worker",
                    stream=stream,
                    group=group,
                    block_ms=10,
                )
                == 1
            )
            assert (
                await consume_once(
                    redis,
                    consumer="integration-worker",
                    stream=stream,
                    group=group,
                    block_ms=10,
                )
                == 0
            )

            detail = await client.get(f"/submissions/{submission_id}")
            assert detail.status_code == 200
            body = detail.json()
            assert body["status"] == "COMPLETED"
            assert body["verdict"] == "ACCEPTED"
            assert len(body["results"]) == 2
            assert all(result["status"] == "ACCEPTED" for result in body["results"])
            assert all(result["runtime_ms"] > 0 for result in body["results"])
            assert all(result["memory_kb"] > 0 for result in body["results"])

            listed = await client.get("/submissions", params={"problem_id": str(problem_id)})
            assert listed.status_code == 200
            assert listed.json()["total"] == 1
    finally:
        if submission_id is not None:
            await redis.xgroup_destroy(stream, group)
        await redis.delete(stream)
        async with SessionFactory() as session:
            if submission_id is not None:
                await session.execute(
                    delete(OutboxEvent).where(OutboxEvent.aggregate_id == submission_id)
                )
                await session.execute(delete(Submission).where(Submission.id == submission_id))
            await session.execute(delete(CaseModel).where(CaseModel.problem_id == problem_id))
            await session.execute(delete(Problem).where(Problem.id == problem_id))
            if user_id is not None:
                await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
        await redis.aclose()
