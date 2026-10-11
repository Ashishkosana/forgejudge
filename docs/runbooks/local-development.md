# Local Development

## Start

```bash
cp .env.example .env
docker compose up --build
```

Use `bash scripts/dev-up.sh` to create `.env` from the safe local template when
needed and start the full stack. The API docs are at
<http://localhost:8000/docs>; the frontend is at <http://localhost:3000>.
The worker runs every test case in a disposable Python container. On Linux,
set `DOCKER_GID` in `.env` to the group ID owning `/var/run/docker.sock`; Compose
prepares the configured `FORGEJUDGE_JUDGE_PYTHON_IMAGE` before the worker starts.
This socket grants broad control of the local Docker daemon, so run the stack
only on a trusted development machine.

When running the worker outside Compose, configure
`FORGEJUDGE_JUDGE_WORKSPACE_VOLUME` and `FORGEJUDGE_JUDGE_WORKSPACE_PATH` to a
shared Docker volume name and its worker-side mount path, and ensure
`FORGEJUDGE_JUDGE_PYTHON_IMAGE` is present in the daemon before processing jobs.

## Verify

```bash
curl --fail http://localhost:8000/health/live
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pytest
python -m ruff check .
pip-audit
npm --prefix frontend ci
npm --prefix frontend audit --audit-level=high
npm --prefix frontend run lint
npm --prefix frontend run typecheck
```

## Stop

```bash
bash scripts/dev-down.sh
```

Use `docker compose down -v` only when intentionally deleting local database
and Redis data volumes. Local Compose ports bind to loopback; do not change
these bindings when using an untrusted network.