# ADR 0003: Authentication and Session Tokens

- Status: Proposed
- Date: 2026-10-11

## Context

Phase 2 has a `users` table with an existing `user`/`admin` role field, but no
authentication. The Next.js frontend currently calls the FastAPI API from
server-rendered pages, while submission records allow a nullable user
reference. Phase 3 needs authentication, ownership checks, and a browser
session without exposing long-lived credentials to JavaScript.

## Proposed decision

- Use FastAPI as the authority for identities, credential verification,
  refresh sessions, and authorization.
- Use a same-origin Next.js backend-for-frontend (BFF) for browser
  authentication and protected API calls.
- Issue short-lived, asymmetrically signed JWT access tokens with pinned
  verification algorithms and validated issuer, audience, expiry, and token
  purpose.
- Issue opaque, high-entropy refresh tokens; persist only their cryptographic
  hashes in PostgreSQL, rotate them on use, and revoke a token family if a
  consumed token is replayed.
- Keep access and refresh credentials in Secure, HttpOnly, SameSite cookies at
  the browser boundary. BFF server handlers forward access tokens as Bearer
  credentials to FastAPI; browser JavaScript never reads tokens.
- Retain `user` and `admin` roles, assign `user` on public registration, and
  authorize admin operations against current database state.
- Keep PostgreSQL authoritative; do not introduce Redis as an auth/session
  source of truth.

## Consequences

- BFF handlers become part of the authentication and CSRF boundary and require
  careful cookie, origin, and error handling.
- Refresh sessions are stateful and require expiration cleanup, rotation,
  revocation, and replay monitoring.
- Short-lived access JWTs reduce but do not eliminate revocation delay; an
  already issued access token may remain valid until expiry unless an explicit
  online revocation check is added.
- API routes still need independent authentication, resource ownership, and
  role checks; hiding UI controls is not authorization.
- Signing keys need managed storage, rotation, and verification-key overlap.
- This ADR remains proposed until product decisions about email verification,
  auth provider, anonymous submissions, cookie domains, token lifetimes, and
  admin bootstrap are approved.

## Alternatives considered

- **Browser localStorage tokens:** rejected because injected JavaScript can
  read persistent credentials.
- **Long-lived JWT refresh tokens:** rejected because revocation and reuse
  detection are difficult without server-side state.
- **Direct cross-origin browser-to-API cookies:** deferred because they
  require broader CORS and cookie-domain coordination and increase CSRF
  configuration complexity.
- **External identity provider only:** left open for future SSO/social login;
  it is not required to establish the initial account/session model.
