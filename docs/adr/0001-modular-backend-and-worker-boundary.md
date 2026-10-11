# ADR 0001: Modular Backend and Worker Boundary

- Status: Accepted
- Date: 2026-10-10

## Context

ForgeJudge needs request/response APIs and potentially long-running,
untrusted code execution. Coupling both workloads to one process would make
resource isolation and independent scaling difficult.

## Decision

Start with a modular Python backend containing distinct API and worker
entrypoints. PostgreSQL is the durable system of record; Redis will coordinate
asynchronous work. The worker will delegate user code to a disposable sandbox
container when the judge engine is implemented.

## Consequences

- API and worker can be tested and scaled independently.
- Queue delivery, retries, idempotency, and lease semantics must be designed
  explicitly in later phases.
- A local worker shell exists now but does not consume jobs.
- No user-provided code is executed by the Phase 0 services.