# Authentication API

FastAPI owns credentials, account state, refresh sessions, and authorization.
Browser traffic goes through the same-origin Next.js BFF; it must not call the
auth endpoints on FastAPI directly.

## Browser/BFF endpoints

| Endpoint | Behavior |
|---|---|
| `GET /api/auth/csrf` | Issues a short-lived CSRF cookie and returns its proof for an unsafe request header. |
| `POST /api/auth/register` | Accepts `email`, `display_name`, and `password`; establishes a session and assigns the `user` role. |
| `POST /api/auth/login` | Accepts `email` and `password`; establishes a session. Invalid credentials have one generic response. |
| `POST /api/auth/session` | Rotates the refresh session and updates the HttpOnly cookies. |
| `GET /api/auth/me` | Returns the sanitized current user. |
| `POST /api/auth/logout` | Revokes the current refresh session and clears cookies. |
| `POST /api/auth/logout-all` | Revokes all refresh sessions for the current user and clears cookies. |

Unsafe BFF requests require an exact same-origin `Origin` and a matching
`X-ForgeJudge-CSRF` header/CSRF cookie. The CSRF proof is not an authentication
credential. Access and refresh cookies are HttpOnly, SameSite=Lax, and Secure
in production; the refresh cookie is scoped to `/api/auth`. Responses to
session operations are not cacheable and expose only the user and access-token
expiry, never the raw access or refresh token.

## Internal FastAPI endpoints

| Endpoint | Protection | Behavior |
|---|---|---|
| `POST /auth/register` | BFF shared-secret header | Creates a user with a password hash and role `user`; `409` for duplicate normalized email. |
| `POST /auth/login` | BFF shared-secret header | Verifies credentials and creates a refresh session; `401` has a generic message. |
| `POST /auth/refresh` | BFF shared-secret header | Rotates one opaque refresh token; invalid, expired, and replayed tokens return `401`. |
| `POST /auth/logout` | BFF shared-secret header | Revokes the presented refresh session; idempotent for absent/unknown tokens. |
| `POST /auth/logout-all` | BFF shared-secret header and access token | Revokes every active refresh session owned by the principal. |
| `GET /auth/me` | Access JWT | Returns `id`, `email`, `display_name`, and the current database role. |
| `GET/POST /submissions` | Access JWT | Lists only the principal's submissions or creates one owned by the principal. |
| `GET /submissions/{id}` | Access JWT | Returns the owner's submission; administrators may inspect any submission. |
| `GET /admin/users` | Current database role `admin` | Returns a bounded list of users; regular users receive `403`. |

FastAPI's `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, and
`/auth/logout-all` responses are internal to the BFF. They include tokens for
server-to-server processing; deployment network policy and the shared secret
must prevent browser clients from bypassing the BFF. `/auth/me` does not
include credential material.

## Credential and rate-limit behavior

- Access tokens use RS256, `kid`, issuer, audience, `sub`, `iat`, `exp`, `jti`,
  and an access-token purpose claim. The API loads the account from PostgreSQL
  and ignores role claims for authorization.
- Passwords are hashed with Argon2id. Raw passwords, JWTs, refresh tokens, and
  token hashes must never be logged.
- Refresh tokens have 384 bits of random entropy. PostgreSQL stores only their
  SHA-256 hashes. Rotation preserves a family ID, with a 7-day idle expiry and
  a 30-day absolute family expiry. Replaying a consumed token revokes every
  active row in its family.
- Redis fixed-window counters limit attempts by source (30/minute) and
  normalized account identity (5/minute). A Redis failure returns `503`, not
  an unthrottled authentication attempt.
- BFF auth operations return `503` until signing/verification keys and a
  shared secret of at least 32 characters are configured.

Configure `FORGEJUDGE_AUTH_PRIVATE_KEY`, the JSON map
`FORGEJUDGE_AUTH_PUBLIC_KEYS` keyed by `kid`,
`FORGEJUDGE_AUTH_SIGNING_KEY_ID`, and `FORGEJUDGE_BFF_SHARED_SECRET` through a
secret manager or trusted runtime environment. Never commit generated keys or
the shared secret.
