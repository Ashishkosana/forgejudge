"""Python execution and per-test-case verdict evaluation."""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from collections.abc import Sequence
from os import chmod
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from backend.common.config import settings
from backend.models.enums import SubmissionVerdict
from backend.models.judging import CaseResult, ExecutionResult, TestCaseInput

OUTPUT_LIMIT = 32_768


class JudgeRunner(Protocol):
    def execute(
        self,
        source_code: str,
        input_data: str,
        *,
        time_limit_ms: int,
        memory_limit_mb: int,
    ) -> ExecutionResult: ...


class DockerPythonRunner:
    """Run one test case in a disposable, resource-limited container."""

    def execute(
        self,
        source_code: str,
        input_data: str,
        *,
        time_limit_ms: int,
        memory_limit_mb: int,
    ) -> ExecutionResult:
        import docker
        import requests

        run_id = uuid4().hex
        workspace_root = Path(settings.judge_workspace_path)
        workspace_root.mkdir(parents=True, exist_ok=True)
        workspace = Path(tempfile.mkdtemp(dir=workspace_root, prefix="case-"))
        chmod(workspace, 0o755)
        container = None
        client = None
        try:
            client = docker.from_env()
            source_path = workspace / "solution.py"
            input_path = workspace / "input.txt"
            launcher_path = workspace / "launcher.py"
            source_path.write_text(source_code)
            input_path.write_text(input_data)
            launcher_path.write_text(Path(__file__).with_name("sandbox_launcher.py").read_text())
            container_started_at = time.monotonic()
            container = client.containers.run(
                settings.judge_python_image,
                command=[
                    "python",
                    "-I",
                    f"/workspace/{workspace.name}/launcher.py",
                    f"/workspace/{workspace.name}/solution.py",
                    f"/workspace/{workspace.name}/input.txt",
                ],
                name=f"forgejudge-case-{run_id}",
                detach=True,
                auto_remove=False,
                user="65534:65534",
                working_dir=f"/workspace/{workspace.name}",
                network_mode="none",
                read_only=True,
                mem_limit=f"{memory_limit_mb}m",
                memswap_limit=f"{memory_limit_mb}m",
                nano_cpus=1_000_000_000,
                pids_limit=32,
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
                tmpfs={
                    "/tmp": "rw,noexec,nosuid,size=16m",
                    "/dev/shm": "rw,noexec,nosuid,size=16m",
                },
                environment={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"},
                volumes={
                    settings.judge_workspace_volume: {"bind": "/workspace", "mode": "ro"}
                },
            )
            remaining_seconds = time_limit_ms / 1000 - (
                time.monotonic() - container_started_at
            )
            if remaining_seconds <= 0:
                try:
                    container.kill()
                except docker.errors.NotFound:
                    pass
                return self._time_limit_result(time_limit_ms)
            try:
                wait_result = container.wait(timeout=remaining_seconds)
            except requests.exceptions.ReadTimeout:
                try:
                    container.kill()
                except docker.errors.NotFound:
                    pass
                return self._time_limit_result(time_limit_ms)

            container.reload()
            if container.attrs["State"]["OOMKilled"]:
                return ExecutionResult(
                    verdict=SubmissionVerdict.MEMORY_LIMIT_EXCEEDED,
                    runtime_ms=time_limit_ms / 1000,
                    memory_kb=memory_limit_mb * 1024,
                    stdout="",
                    stderr="Memory limit exceeded",
                )
            if wait_result["StatusCode"] != 0:
                error_output = container.logs(stdout=False, stderr=True)
                return ExecutionResult(
                    verdict=SubmissionVerdict.RUNTIME_ERROR,
                    runtime_ms=None,
                    memory_kb=None,
                    stdout="",
                    stderr=error_output.decode("utf-8", errors="replace")[:OUTPUT_LIMIT],
                )
            output = container.logs(stdout=True, stderr=False).decode("utf-8")
            execution = json.loads(output)
            if execution["oom_killed"]:
                verdict = SubmissionVerdict.MEMORY_LIMIT_EXCEEDED
            elif execution["return_code"] != 0:
                verdict = SubmissionVerdict.RUNTIME_ERROR
            else:
                verdict = SubmissionVerdict.ACCEPTED
            stderr = execution["stderr"]
            if execution["stdout_truncated"] or execution["stderr_truncated"]:
                stderr = f"{stderr}\nProgram output exceeded {OUTPUT_LIMIT} bytes.".strip()
            if execution["stdout_truncated"]:
                verdict = SubmissionVerdict.WRONG_ANSWER
            return ExecutionResult(
                verdict=verdict,
                runtime_ms=float(execution["runtime_ms"]),
                memory_kb=int(execution["memory_kb"]),
                stdout=str(execution["stdout"]),
                stderr=str(stderr),
            )
        finally:
            try:
                if client is not None and container is not None:
                    try:
                        container.remove(force=True)
                    except docker.errors.NotFound:
                        pass
            finally:
                try:
                    if client is not None:
                        client.close()
                finally:
                    shutil.rmtree(workspace)

    @staticmethod
    def _time_limit_result(time_limit_ms: int) -> ExecutionResult:
        return ExecutionResult(
            verdict=SubmissionVerdict.TIME_LIMIT_EXCEEDED,
            runtime_ms=float(time_limit_ms),
            memory_kb=None,
            stdout="",
            stderr="Time limit exceeded",
        )


def evaluate_submission(
    source_code: str,
    test_cases: Sequence[TestCaseInput],
    *,
    time_limit_ms: int,
    memory_limit_mb: int,
    runner: JudgeRunner,
) -> tuple[list[CaseResult], SubmissionVerdict]:
    if not test_cases:
        raise ValueError("Cannot judge a problem without test cases")

    results: list[CaseResult] = []
    for test_case in test_cases:
        execution = runner.execute(
            source_code,
            test_case.input_data,
            time_limit_ms=time_limit_ms,
            memory_limit_mb=memory_limit_mb,
        )
        verdict = execution.verdict
        if verdict == SubmissionVerdict.ACCEPTED and (
            execution.stdout.split() != test_case.expected_output.split()
        ):
            verdict = SubmissionVerdict.WRONG_ANSWER
        results.append(
            CaseResult(
                test_case_id=test_case.id,
                verdict=verdict,
                runtime_ms=execution.runtime_ms,
                memory_kb=execution.memory_kb,
                stdout=execution.stdout,
                stderr=execution.stderr,
            )
        )

    submission_verdict = next(
        (result.verdict for result in results if result.verdict != SubmissionVerdict.ACCEPTED),
        SubmissionVerdict.ACCEPTED,
    )
    return results, submission_verdict
