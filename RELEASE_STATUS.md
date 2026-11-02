# VEYA — Release Status (single source of truth)
Version **0.5.3** · 2026-10-30 · **Decision: NOT READY — BLOCKERS REMAIN** (0.6 has NOT been started)

`bash tools/audit/run_all.sh` → exit **2** in the authoring sandbox (PASS 11 · FAIL 0 · BLOCKED 8 · NOT_RUN 1): nothing failed, but the core checks could not run.
Exit **0** on a connected machine is required for READY FOR 0.6. Full evidence: `docs/AUDIT_REPORT_0.5.3.md`. How to run what was blocked: `docs/RUN_BLOCKED_CHECKS.md` ("QUICK PATH").

**Working from a phone only?** → `docs/RUN_FROM_PHONE.md` (GitHub Actions workflow `cloud/audit.yml`; **written, not yet executed on GitHub**).

## Why blocked
No network (PyPI/npm return HTTP code 000), so Django, DRF, pytest, psycopg, Jest, Expo cannot be installed; no PostgreSQL/Docker; no emulator. Nothing below is claimed as passed unless it says EXECUTED — PASS.

## Features
| Release | Content | Backend code | Backend tests | Mobile |
|---|---|---|---|---|
| 0.1 | auth (JWT), profile, privacy | WRITTEN — NOT EXECUTED | WRITTEN — NOT EXECUTED | WRITTEN — NOT EXECUTED |
| 0.2 | posts, follows (private by default), feed, search | same | same | same |
| 0.3 | blocks, reports (admin review), likes, comments | same | same | same |
| 0.4 | image upload (re-encode, EXIF stripped, signed URLs) | pipeline + signing **EXECUTED — PASS** (35 hostile/valid inputs, real Pillow); views WRITTEN — NOT EXECUTED | WRITTEN — NOT EXECUTED | WRITTEN — NOT EXECUTED |
| 0.5 | in-app notifications | WRITTEN — NOT EXECUTED | WRITTEN — NOT EXECUTED | WRITTEN — NOT EXECUTED |
| 0.5.3 | age gate, security log, e-mail unsubscribe mechanism (ADR-0026) | pure logic **EXECUTED — PASS**; Django layer WRITTEN — NOT EXECUTED | 179 Django-dependent test functions WRITTEN — NOT EXECUTED; 34 pure tests **EXECUTED — PASS** | date parsing **EXECUTED — PASS** (shim); screens WRITTEN — NOT EXECUTED |

## Verification table
| Check | Status |
|---|---|
| `manage.py check`, `makemigrations --check --dry-run`, `showmigrations`, `migrate` on a fresh DB, `pytest` (179 Django-dependent functions) | **BLOCKED** (no Django / PostgreSQL / network) |
| `npm ci` | **NOT_RUN** — no `package-lock.json` (needs network once: `npm install`, then commit the lock) |
| `npx tsc --noEmit`, `npx jest` (incl. `AuthContext.test.tsx`), app run, end-to-end | **BLOCKED** (no `node_modules`, no emulator) |
| Backend pure-logic tests (age rules, security-log helpers, redaction, e-mail tokens/policy) | **EXECUTED — PASS** 34/34 |
| Image pipeline + signed URLs, real Pillow 12.1.1 (project pins 11.0.0) | **EXECUTED — PASS** 35/35 |
| Mobile pure-function tests (43 `it` cases) with a tiny shim runner — **not Jest** | **EXECUTED — PASS** 43/43 |
| Model ↔ migration consistency (10 apps, 13 hand-written migrations; checker v2, 26 defect tests) | **STATICALLY VERIFIED** (not Django's autodetector) |
| Backend Python static (148 files parse, local imports resolve, no undefined names) | **STATICALLY VERIFIED** |
| Serializer/route boundary scripts, repo hygiene (no secrets, no `.env`, no third-party font/CDN/analytics hosts) | **STATICALLY VERIFIED** |
| Audit tooling itself: 69 unit tests; 27 failure-injection cases for `run_all.sh`/`collect_report.sh` | **EXECUTED — PASS** |

## Compliance (owner's four rules) — see `docs/COMPLIANCE_PLAN.md`
1. **Age at signup** — implemented (server-authoritative, neutral error, same-e-mail cooldown, only birth year+month stored). **Minimum age undecided [COUNSEL]**; dev placeholder 16; production refuses to start without `VEYA_MINIMUM_AGE`.
2. **Local fonts** — verified: system fonts only, nothing added, nothing external.
3. **Security/session logs** — implemented with truncated IP, no credentials, log redaction; retention 90 days is a **proposal [COUNSEL]**; purge job must still be scheduled.
4. **Marketing unsubscribe** — mechanism implemented (signed link, one-click POST, suppression list, opt-in consent, transactional ≠ marketing) but **NOT ACTIVATED**: no e-mail is sent.
Not done: account deletion/export, privacy policy + terms + acceptance record, minors safeguards beyond the gate.
None of this is a claim of legal compliance or protection from fines.

## Known limits
Cooldown/throttle counters are per-process until a shared cache (Redis) exists · self-declared age is bypassable · SimpleJWT 5.3.1 / django-cors-headers 4.4.0 predate official Django 5.1 support (unverified until pytest runs) · notifications are polled (no push) · image bytes are streamed through Django.

## Next steps (in order)
1. On a connected machine run the QUICK PATH in `docs/RUN_BLOCKED_CHECKS.md`; send `audit_report_*.txt` (from `collect_report.sh`).
2. Fix what real `pytest`/`tsc`/Jest show (evidence first, tests with each fix); commit `mobile/package-lock.json`.
3. Owner/counsel decisions listed in the audit report §6.
4. Only when `run_all.sh` exits 0: READY FOR 0.6.
