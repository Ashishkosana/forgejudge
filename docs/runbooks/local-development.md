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

## Authentication setup

Authentication endpoints deliberately return `503` until the API has its
RS256 signing key, the corresponding public-key map, and a BFF shared secret
of at least 32 characters. Generate development-only keys outside the
repository and export them into the same shell that runs Compose:

```bash
install -d -m 700 "$HOME/.config/forgejudge"
umask 077
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 \
  -out "$HOME/.config/forgejudge/auth-private.pem"
openssl pkey -in "$HOME/.config/forgejudge/auth-private.pem" -pubout \
  -out "$HOME/.config/forgejudge/auth-public.pem"
export FORGEJUDGE_AUTH_PRIVATE_KEY="$(cat "$HOME/.config/forgejudge/auth-private.pem")"
export FORGEJUDGE_AUTH_PUBLIC_KEYS="$(python -c 'import json,pathlib; print(json.dumps({"local": pathlib.Path.home().joinpath(".config/forgejudge/auth-public.pem").read_text()}))')"
export FORGEJUDGE_AUTH_SIGNING_KEY_ID=local
export FORGEJUDGE_BFF_SHARED_SECRET="$(openssl rand -hex 32)"
docker compose up --build
```

The public-key setting is a JSON object keyed by `kid`; retain old public keys
during signing-key rotation until tokens signed by them have expired. These
exports are not persisted in `.env`; use the deployment secret manager for
shared environments. Never commit private keys or shared secrets.

The first administrator must be provisioned by an approved, audited operator
procedure after registering an account. Public registration always creates a
regular user, and no API endpoint accepts role changes.

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