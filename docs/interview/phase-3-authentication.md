# Phase 3 Authentication: Interview Guide

## Short architecture pitch

FastAPI remains the source of truth for identities and authorization. A
same-origin Next.js backend-for-frontend (BFF) handles browser authentication,
so browser JavaScript never sees access or refresh tokens. PostgreSQL persists
users and hashed, revocable refresh sessions. Redis provides bounded
source/account rate limiting but is not the session authority.

## Sign-in and refresh data flow

```mermaid
sequenceDiagram
    participant Browser
    participant BFF as Next.js BFF
    participant API as FastAPI
    participant Redis
    participant DB as PostgreSQL
    Browser->>BFF: Email/password + CSRF header
    BFF->>API: Credential request + private BFF shared secret
    API->>Redis: Increment hashed source/account counters
    API->>DB: Load or create user; persist refresh-token hash
    API-->>BFF: Short-lived access JWT + opaque refresh token
    BFF-->>Browser: HttpOnly cookies + sanitized user
    Browser->>BFF: Refresh request + CSRF proof
    BFF->>API: Refresh token + BFF secret
    API->>DB: Lock old session, revoke it, insert replacement
    API-->>BFF: New access JWT and refresh token
    BFF-->>Browser: Rotate cookies; return no token values
```

The BFF verifies the `Origin` and a double-submit CSRF token for unsafe
requests. The CSRF value is not an authentication credential. Access cookies
are HttpOnly, SameSite=Lax, Secure in production; refresh cookies are also
HttpOnly and scoped to the BFF auth routes.

## Storage and token choices

- The `users` record includes nullable `password_hash`, nullable
  `email_verified_at`, `is_active`, and `last_login_at`. Public registration
  accepts no role field and always stores `user`.
- `refresh_sessions` stores a unique SHA-256 token hash, user/family IDs,
  expiry, revocation, use time, and replacement lineage. The raw token is
  random and returned only to the BFF.
- Migration `0004` adds auth state and refresh sessions after checking for
  case-insensitive email collisions. `0005` adds a 30-day absolute family
  expiry while preserving existing refresh rows.
- A 10-minute RS256 JWT carries a user UUID, issuer, audience, issue/expiry
  times, unique token ID, and access purpose. The role is deliberately loaded
  from the database on every authenticated request.

## Authorization

The API requires an active user for submission create/list/detail operations.
Creation assigns `submission.user_id` from the verified principal rather than
from the request body. Lists filter by owner; the admin override is derived
from the current database role, never from a caller parameter or stale JWT
claim. A non-owner detail request returns `404` to avoid disclosing whether
another user's submission exists. `/admin/users` is separately protected and
returns `403` for ordinary users.

Public problem browsing remains anonymous. Historical submissions with a
null owner remain in the database, but new submissions require authentication.
Administrator provisioning is an operator responsibility; no client-facing
role mutation path exists.

## Why rotation and family revocation?

Opaque refresh tokens are easier to revoke than long-lived JWTs because the
server owns a row for each active session. Each successful refresh locks and
consumes the old row in the same transaction that creates its replacement.
Seeing a consumed token again signals theft or a race/replay, so the whole
family is revoked and the client must authenticate again. A 7-day idle expiry
and 30-day absolute expiry bound session duration.

Access JWTs are stateless and can remain valid until their 10-minute expiry
after logout. If product requirements need immediate access-token revocation,
an online token-version or denylist check is a separate availability/performance
trade-off; the current design does not claim immediate revocation.

## Verification and honest caveats

Focused tests cover password/JWT primitives, input contracts, BFF fail-closed
configuration, rate-limit key privacy, submission ownership, and non-admin
denial. PostgreSQL-backed refresh rotation/replay/expiry tests are included but
need a dedicated database. Compose and full browser verification also need
Docker; those checks were unavailable in the rebuilt Codespace and must not be
represented as passing.
