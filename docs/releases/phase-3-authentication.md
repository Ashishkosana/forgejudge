# Phase 3: Authentication and Authorization

## Implemented

- Added `0004_authentication` for user credential/account state and refresh
  sessions, plus `0005_refresh_family_expiry` for an absolute refresh-family
  expiry.
- Added Argon2id password hashing, RS256 access JWTs, opaque hashed refresh
  tokens, transactional rotation, replay-family revocation, logout, and
  all-session logout.
- Added registration, login, refresh, logout, current-user, and admin-user
  endpoints. Registration always assigns the ordinary `user` role.
- Added source/account rate limits that fail closed when Redis is unavailable.
- Protected submission creation, listing, and detail retrieval with
  authenticated ownership checks; administrators can list all users and view
  all submissions.
- Added same-origin Next.js authentication BFF routes, CSRF proofs,
  HttpOnly cookies, sign-in/registration pages, and session navigation.
- Added API, architecture, ADR, and interview documentation.

## Verification status

### Passed in the current Codespace

- Backend unit and contract tests.
- Ruff.
- Frontend lint, typecheck, and production build.

### Skipped or not run

- **Skipped:** PostgreSQL/Redis integration tests; no test database or live
  services are configured in this Codespace.
- **NOT RUN:** `docker compose config`.
- **NOT RUN:** `docker compose build`.
- **NOT RUN:** `docker compose up -d`.
- **NOT RUN:** `docker compose ps`.
- **NOT RUN:** Full PostgreSQL/Redis integration tests against live services.
- **NOT RUN:** Browser authentication end-to-end tests.

These are outstanding release gates, not passing checks. The draft PR must
remain a draft until the Docker Compose, live database/Redis integration, and
browser authentication end-to-end gates have run successfully in an
environment with the required services.

## Operational requirements and limitations

- Configure an RS256 private key, a public-key JSON map with the active `kid`,
  and a random BFF shared secret outside source control. Auth routes fail
  closed when required settings are absent.
- Email verification, password recovery, MFA, external identity providers, and
  immediate access-token revocation are out of scope.
- Provision the first administrator through an approved operator process.
  There is no public or self-service role-change endpoint.
- Existing anonymous submission records are preserved; new submissions and
  submission history require login.
