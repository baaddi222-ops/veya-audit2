# ADR-0016: JWT via djangorestframework-simplejwt

Date: 2026-09-30
Status: Accepted
Release: VEYA 0.1 (stack pivot)

## Decision
Mobile authentication uses JSON Web Tokens issued by
`djangorestframework-simplejwt`: short-lived access tokens (15 min),
rotated refresh tokens (30 days) with blacklisting.

## Context / Problem
Supabase Auth previously issued and managed JWTs, session refresh, and
token revocation for us. A self-built Django backend needs an explicit
choice for mobile-client authentication.

## Alternatives Considered
- Django session-based auth (cookies): the traditional Django default, but
  awkward for a mobile client (no persistent cookie jar the way a browser
  has); JWT is the standard, well-documented pattern for DRF + mobile.
- Rolling a custom token scheme: unnecessary risk — `simplejwt` is mature,
  widely used, and already solves rotation/blacklisting correctly.

## Reason for Decision
`simplejwt` is the de facto standard for this exact pairing (DRF backend +
mobile client), with rotation and blacklisting support built in — avoiding
hand-rolled token logic for a security-critical feature.

## Consequences
Token blacklisting on logout must be deliberately called (`LogoutView`) —
unlike Supabase Auth, this is not automatic. The mobile app must handle
token refresh itself (a follow-up item once the access token expires
mid-session — not yet implemented, tracked as a known limitation).
