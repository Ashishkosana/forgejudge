# ADR 0002: Isolated Python Judge Execution

- Status: Accepted
- Date: 2026-10-10

## Context

The worker previously acknowledged queued submissions without executing code.
The judge needs deterministic per-test-case outcomes and resource metrics while
keeping untrusted submissions out of the API and worker processes.

## Decision

The worker delegates each test case to a fresh Docker container based on the
configured Python 3.12 runtime image. Each container has networking disabled,
a read-only root filesystem and workspace, a non-root UID, no Linux
capabilities, `no-new-privileges`, a PID limit, one CPU, a problem-specific
memory/swap cap, and a wall-clock timeout. A small launcher runs the submitted
program, caps retained stdout and stderr, and reports runtime, peak memory, and
the program exit status. Results are persisted per case; the submission verdict
is the first non-accepted case verdict in test-case order.

Docker daemon access is an explicit trust boundary. Local Compose mounts the
host socket only to support development. Production deployments must use a
dedicated isolated rootless daemon or a separately secured runner service.

## Consequences

- A Docker-compatible daemon, a shared workspace volume, and the configured
  runtime image are required to evaluate submissions.
- Python 3.12 is the initial supported language.
- User-code resource failures become completed submissions with explicit
  verdicts; runner/daemon failures mark a submission failed.
- Each case incurs container startup overhead and is run independently.
- Container limits constrain submitted code, but the worker's daemon access
  remains highly privileged and must be isolated in production.
