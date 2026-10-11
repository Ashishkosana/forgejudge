"""Launch submitted Python code and return bounded output and process metrics."""

import json
import resource
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import BinaryIO

OUTPUT_LIMIT_BYTES = 32_768


def read_bounded(stream: BinaryIO, output: bytearray, truncated: threading.Event) -> None:
    while chunk := stream.read(4096):
        remaining = OUTPUT_LIMIT_BYTES - len(output)
        if len(chunk) > remaining:
            truncated.set()
        if remaining > 0:
            output.extend(chunk[:remaining])


def oom_kill_count() -> int:
    try:
        events = Path("/sys/fs/cgroup/memory.events").read_text()
    except (FileNotFoundError, PermissionError):
        return 0
    for line in events.splitlines():
        key, value = line.split()
        if key == "oom_kill":
            return int(value)
    return 0


def memory_peak_kb() -> int | None:
    try:
        peak_bytes = int(Path("/sys/fs/cgroup/memory.peak").read_text())
    except (FileNotFoundError, PermissionError):
        return None
    return peak_bytes // 1024


def main() -> int:
    source_path = Path(sys.argv[1])
    input_path = Path(sys.argv[2])
    oom_kills_before = oom_kill_count()
    started_at = time.monotonic()
    with input_path.open("rb") as stdin:
        process = subprocess.Popen(
            [sys.executable, "-I", "-B", str(source_path)],
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert process.stdout is not None
        assert process.stderr is not None
        stdout = bytearray()
        stderr = bytearray()
        stdout_truncated = threading.Event()
        stderr_truncated = threading.Event()
        stdout_reader = threading.Thread(
            target=read_bounded, args=(process.stdout, stdout, stdout_truncated)
        )
        stderr_reader = threading.Thread(
            target=read_bounded, args=(process.stderr, stderr, stderr_truncated)
        )
        stdout_reader.start()
        stderr_reader.start()
        return_code = process.wait()
        stdout_reader.join()
        stderr_reader.join()

    runtime_ms = (time.monotonic() - started_at) * 1000
    memory_kb = memory_peak_kb()
    if memory_kb is None:
        memory_kb = int(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    result = {
        "return_code": return_code,
        "runtime_ms": runtime_ms,
        "memory_kb": memory_kb,
        "oom_killed": oom_kill_count() > oom_kills_before,
        "stdout": stdout.decode("utf-8", errors="replace"),
        "stderr": stderr.decode("utf-8", errors="replace"),
        "stdout_truncated": stdout_truncated.is_set(),
        "stderr_truncated": stderr_truncated.is_set(),
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
