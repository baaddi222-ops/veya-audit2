# ADR-0015: Django + Django REST Framework for the backend

Date: 2026-09-30
Status: Accepted
Release: VEYA 0.1 (stack pivot)

## Decision
Replace Supabase (managed Postgres + Auth + PostgREST + RLS) with a
self-built Django + Django REST Framework backend, per explicit product
direction to rebuild on the technology stack Instagram's backend used
(Python/Django + PostgreSQL).

## Context / Problem
The project owner directed a full stack pivot away from Flutter/Supabase.
PostgreSQL is kept per an explicit decision (also Instagram's actual
database choice); the application/API layer needs a Python framework to
replace what Supabase's managed services previously provided.

## Alternatives Considered
- Flask/FastAPI: lighter-weight, but would require hand-building auth
  scaffolding, an ORM/migration system, and an admin interface that Django
  provides out of the box — more code to secure ourselves for no clear
  benefit at this project's scale.
- Keeping Supabase and only changing the mobile framework: rejected — the
  explicit direction was a full-stack rebuild on Django/PostgreSQL +
  React Native, not a partial change.

## Reason for Decision
Django's migration system, built-in auth scaffolding, and ORM reduce the
amount of custom security-critical code this project has to build and
maintain itself — the same reasoning ADR-0001 used for choosing Supabase
originally, now applied to Django as the specifically-directed replacement.

## Consequences
The RLS-based security model (ADR-0007, 0.1-C's column-grant hardening)
has no direct equivalent — authorization moves entirely into Django view
code. See ADR-0019 for how this is mitigated. All Flutter/Supabase-era
code becomes historical reference, not a migration source — re-derived per
this stack's idioms rather than mechanically ported.
