"""Claim submissions, evaluate them, and persist per-case results."""

import asyncio
from uuid import UUID

from backend.common.database import SessionFactory
from backend.models.enums import SubmissionStatus
from backend.models.judging import TestCaseInput
from backend.repositories.submissions import SubmissionsRepository
from backend.worker.judge import DockerPythonRunner, JudgeRunner, evaluate_submission


async def process_submission(
    submission_id: UUID, *, runner: JudgeRunner | None = None
) -> bool:
    repository = SubmissionsRepository()
    async with SessionFactory() as session:
        submission = await repository.get_for_processing(session, submission_id)
        if submission is None or submission.status in (
            SubmissionStatus.COMPLETED.value,
            SubmissionStatus.FAILED.value,
        ):
            return False
        if submission.status == SubmissionStatus.QUEUED.value:
            claimed = await repository.mark_running(session, submission_id)
            if not claimed:
                return False
            await session.commit()
            submission = await repository.get_for_processing(session, submission_id)
            if submission is None or submission.status != SubmissionStatus.RUNNING.value:
                return False

        test_cases = [
            TestCaseInput(
                id=test_case.id,
                input_data=test_case.input_data,
                expected_output=test_case.expected_output,
            )
            for test_case in submission.problem.test_cases
        ]
        case_results, verdict = await asyncio.to_thread(
            evaluate_submission,
            submission.source_code,
            test_cases,
            time_limit_ms=submission.problem.time_limit_ms,
            memory_limit_mb=submission.problem.memory_limit_mb,
            runner=runner or DockerPythonRunner(),
        )
        await repository.complete_with_evaluation(session, submission, case_results, verdict)
        await session.commit()
    return True
