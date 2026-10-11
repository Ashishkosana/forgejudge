"""Unit tests for judge evaluation and sandbox configuration."""

import json
import sys
import threading
from io import BytesIO
from pathlib import Path
from types import ModuleType, SimpleNamespace
from uuid import uuid4

import pytest
from backend.models.enums import SubmissionVerdict
from backend.models.judging import ExecutionResult, TestCaseInput
from backend.worker.judge import DockerPythonRunner, evaluate_submission
from backend.worker.sandbox_launcher import OUTPUT_LIMIT_BYTES, read_bounded


class FakeRunner:
    def __init__(self, outcomes: dict[str, ExecutionResult]) -> None:
        self.outcomes = outcomes
        self.calls: list[tuple[str, int, int]] = []

    def execute(
        self,
        source_code: str,
        input_data: str,
        *,
        time_limit_ms: int,
        memory_limit_mb: int,
    ) -> ExecutionResult:
        self.calls.append((input_data, time_limit_ms, memory_limit_mb))
        return self.outcomes[input_data]


def make_test_case(input_data: str, expected_output: str) -> TestCaseInput:
    return TestCaseInput(uuid4(), input_data, expected_output)


def make_execution(
    verdict: SubmissionVerdict,
    *,
    stdout: str = "",
    stderr: str = "",
) -> ExecutionResult:
    return ExecutionResult(verdict, 12.5, 2048, stdout, stderr)


@pytest.mark.parametrize(
    ("payload_size", "expected_truncated"),
    [(OUTPUT_LIMIT_BYTES, False), (OUTPUT_LIMIT_BYTES + 1, True)],
)
def test_read_bounded_reports_only_actual_truncation(
    payload_size: int, expected_truncated: bool
) -> None:
    output = bytearray()
    truncated = threading.Event()

    read_bounded(BytesIO(b"x" * payload_size), output, truncated)

    assert len(output) == min(payload_size, OUTPUT_LIMIT_BYTES)
    assert truncated.is_set() is expected_truncated


def test_evaluate_submission_records_every_case_and_metrics() -> None:
    cases = [
        make_test_case("first", "expected"),
        make_test_case("second", "also expected"),
        make_test_case("third", "not used"),
    ]
    runner = FakeRunner(
        {
            "first": make_execution(SubmissionVerdict.ACCEPTED, stdout="  expected\n"),
            "second": make_execution(SubmissionVerdict.ACCEPTED, stdout="wrong"),
            "third": make_execution(
                SubmissionVerdict.RUNTIME_ERROR, stderr="Traceback: failure"
            ),
        }
    )

    results, verdict = evaluate_submission(
        "print('answer')",
        cases,
        time_limit_ms=500,
        memory_limit_mb=64,
        runner=runner,
    )

    assert [result.verdict for result in results] == [
        SubmissionVerdict.ACCEPTED,
        SubmissionVerdict.WRONG_ANSWER,
        SubmissionVerdict.RUNTIME_ERROR,
    ]
    assert verdict == SubmissionVerdict.WRONG_ANSWER
    assert [result.test_case_id for result in results] == [case.id for case in cases]
    assert results[0].runtime_ms == 12.5
    assert results[0].memory_kb == 2048
    assert results[2].stderr == "Traceback: failure"
    assert runner.calls == [("first", 500, 64), ("second", 500, 64), ("third", 500, 64)]


@pytest.mark.parametrize(
    "case_verdict",
    [
        SubmissionVerdict.WRONG_ANSWER,
        SubmissionVerdict.RUNTIME_ERROR,
        SubmissionVerdict.TIME_LIMIT_EXCEEDED,
        SubmissionVerdict.MEMORY_LIMIT_EXCEEDED,
    ],
)
def test_first_failing_case_sets_submission_verdict(case_verdict: SubmissionVerdict) -> None:
    case = make_test_case("input", "expected")
    runner = FakeRunner({"input": make_execution(case_verdict)})

    results, verdict = evaluate_submission(
        "pass",
        [case],
        time_limit_ms=100,
        memory_limit_mb=32,
        runner=runner,
    )

    assert results[0].verdict == case_verdict
    assert verdict == case_verdict


def test_evaluate_submission_rejects_problems_without_test_cases() -> None:
    with pytest.raises(ValueError, match="without test cases"):
        evaluate_submission(
            "pass",
            [],
            time_limit_ms=100,
            memory_limit_mb=32,
            runner=FakeRunner({}),
        )


def test_docker_runner_applies_container_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result_payload = {
        "return_code": 0,
        "runtime_ms": 2.5,
        "memory_kb": 1024,
        "oom_killed": False,
        "stdout": "42\n",
        "stderr": "",
        "stdout_truncated": False,
        "stderr_truncated": False,
    }
    captured: dict[str, object] = {}

    class FakeContainer:
        attrs = {"State": {"OOMKilled": False}}

        def wait(self, *, timeout: float) -> dict[str, int]:
            captured["timeout"] = timeout
            return {"StatusCode": 0}

        def reload(self) -> None:
            pass

        def logs(self, *, stdout: bool, stderr: bool) -> bytes:
            assert stdout and not stderr
            return json.dumps(result_payload).encode()

        def remove(self, *, force: bool) -> None:
            assert force

    class FakeContainers:
        def run(self, image: str, **kwargs: object) -> FakeContainer:
            captured["image"] = image
            captured.update(kwargs)
            return FakeContainer()

    class FakeClient:
        containers = FakeContainers()

        def close(self) -> None:
            pass

    docker_module = ModuleType("docker")
    docker_module.from_env = lambda: FakeClient()
    docker_module.errors = SimpleNamespace(NotFound=type("NotFound", (Exception,), {}))
    requests_module = ModuleType("requests")
    requests_module.exceptions = SimpleNamespace(ReadTimeout=TimeoutError)
    monkeypatch.setitem(sys.modules, "docker", docker_module)
    monkeypatch.setitem(sys.modules, "requests", requests_module)
    monkeypatch.setattr("backend.worker.judge.settings.judge_workspace_path", str(tmp_path))
    monkeypatch.setattr("backend.worker.judge.settings.judge_workspace_volume", "judge-workspaces")
    monkeypatch.setattr("backend.worker.judge.settings.judge_python_image", "python:test")

    result = DockerPythonRunner().execute(
        "print(42)",
        "input",
        time_limit_ms=250,
        memory_limit_mb=48,
    )

    assert result.verdict == SubmissionVerdict.ACCEPTED
    assert result.runtime_ms == 2.5
    assert result.memory_kb == 1024
    assert result.stdout == "42\n"
    assert captured["image"] == "python:test"
    assert captured["network_mode"] == "none"
    assert captured["read_only"] is True
    assert captured["mem_limit"] == "48m"
    assert captured["memswap_limit"] == "48m"
    assert captured["pids_limit"] == 32
    assert captured["cap_drop"] == ["ALL"]
    assert captured["user"] == "65534:65534"
    assert captured["volumes"] == {
        "judge-workspaces": {"bind": "/workspace", "mode": "ro"}
    }
