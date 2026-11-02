# ADR-0019: View-layer-only authorization (no RLS equivalent)

Date: 2026-09-30
Status: Accepted
Release: VEYA 0.1 (stack pivot)

## Decision
Authorization for user-owned data (profiles, privacy settings) is enforced
entirely in Django view code (`get_object()` resolving only from
`request.user`, closed-field serializers, an `IsActiveAccountOwner`
permission class) — there is no database-level Row Level Security
equivalent in this stack.

## Context / Problem
Supabase's RLS meant the database itself was the final, un-bypassable
authorization boundary regardless of application code correctness. Django
connects to Postgres with one shared, privileged role — there is no
built-in per-request database-level authorization layer.

## Alternatives Considered
- Adopt Postgres RLS anyway, with Django manually setting a session
  variable per request (`SET LOCAL app.current_user_id`) and RLS policies
  referencing it: possible, and worth reconsidering once real users exist,
  but adds real complexity (a middleware to manage the session variable
  correctly per-request, careful connection-pooling interaction) not
  justified for a 0.1 foundation with no data yet. Noted as a legitimate
  future hardening option, not adopted now — avoiding premature complexity
  per the master spec's own principle.
- Row-level checks via a shared base viewset class: adopted in spirit —
  `get_object()`'s "always from request.user" pattern is meant to be the
  one place this logic lives, reused rather than re-implemented per view.

## Reason for Decision
For a 0.1 foundation with two tables and two endpoints, comprehensive view-layer
tests are achievable and auditable. The database-level RLS alternative's
complexity is not justified yet — but the gap it leaves (no backstop if a
future view is written carelessly) is real and is disclosed plainly in
`docs/SECURITY_DECISIONS.md` rather than minimized.

## Consequences
Every future endpoint that touches user-owned data must be reviewed against
this same discipline (identity from `request.user` only, closed serializer
field lists) — there is no safety net if that discipline lapses. The test
suite (`test_profile_ownership.py`) is the primary place this gets caught,
and must grow with the API, not lag behind it.
