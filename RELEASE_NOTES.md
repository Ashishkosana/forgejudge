# Release Notes

## Phase 2 — Judge Engine (2026-10-10)

### Added

- Python 3.12 execution in a fresh, network-disabled Docker container for each
  test case.
- Accepted, wrong-answer, runtime-error, time-limit, and memory-limit verdicts
  with persisted per-case results.
- Per-case runtime and peak-memory metrics, plus bounded stdout/stderr capture.
- Container restrictions for memory, CPU, process count, filesystem access,
  Linux capabilities, and privilege escalation.
- Docker runner configuration, local Compose workspace sharing, tests, and
  architecture decision record 0002.

### Notes

- Python 3.12 is the only supported language.
- Output matching ignores whitespace between tokens.
- Local Compose requires access to the Docker socket; use it only on a trusted
  development machine. Production should use an isolated rootless daemon or a
  separately secured runner service.
