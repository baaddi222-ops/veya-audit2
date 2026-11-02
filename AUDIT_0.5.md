> **Superseded for current status by `docs/AUDIT_REPORT_0.5.3.md` and `docs/RELEASE_STATUS.md`.** This file is the history of earlier audit rounds (0.5.1/0.5.2).

# VEYA 0.5.2 — Audit tooling fixes & release verification (addendum)
Date: 2026-10-27/28 · Input: `veya-0_5_1-audit-django-rn.zip` (kept as `BACKUP_veya-0_5_1-audit-django-rn.zip`) · Output: `veya-0_5_2-audit-fixes.zip`
No feature of 0.1–0.5 was removed, no backend source/auth/block/privacy logic was changed, nothing from 0.6 was started.

## A. Environment (re-verified)
Python 3.12.3 · Node 22.22.2 · `tsc` 6.0.3 · Pillow 12.1.1 · SQLite module 3.45.1. **No network**: `curl https://pypi.org/simple/django/` → HTTP code 000, `curl https://registry.npmjs.org/expo` → 000,
`pip download django==5.1.3` → "No matching distribution", `npm view expo version` (with the sandbox `.npmrc` bypassed) → `npm error network`. No PostgreSQL, Docker, Jest, Expo, emulator.
Not installed: django, djangorestframework, simplejwt, django-environ, corsheaders, psycopg, pytest, pytest-django. **BLOCKED reason: no package index reachable.**

## B. What changed in 0.5.2 and why
| File | Change | Reason (evidence) |
|---|---|---|
| `tools/audit/run_all.sh` | rewritten: `set -Eeuo pipefail`; per-check `PASS/FAIL/BLOCKED/NOT_RUN`; exit **0/1/2** (2 = nothing failed but checks could not run); no `tail`, no `|| true`, child exit codes never masked; real Django/Jest steps added (BLOCKED here) | the 0.5.1 script piped steps into `tail` and ignored `tsc` failures, so a failing check could still end with exit 0. Writing the new one also exposed (and I fixed before shipping) a `sed|head` SIGPIPE crash (exit 141) and a `tsc 6` `TS5107` config error that the old script had silently ignored |
| `tools/audit/selftest_run_all.sh` (new) | 19 failure-injection cases | proves exit 1 on 15 injected defects (serializer `__all__`, migration drift, GIF accepted, EXIF kept, JWT `atob` bug re-introduced, TS syntax error, undefined identifier, broken relative import, `.env`, Google Fonts, crashing script, deleted tool, checker disabled, missing interpreter) and exit 2 (never 0) when tools are missing |
| `tools/audit/check_migrations.py` | v2 (was v1) | v1 compared names/types/few kwargs only. v2 also compares defaults, choices, validators, null/blank/unique/db_index, FK targets/on_delete/related_name, Meta ordering, index & constraint **definitions** (Q normalised), inherited `AbstractBaseUser`/`PermissionsMixin` fields, per-file dependencies/cycles/cross-app coverage, apps without migrations; uninterpretable constructs are reported as UNVERIFIED (exit 2) instead of skipped |
| `tools/audit/tests/` (new) | 56 `unittest` tests | 26 checker tests with deliberate defects (each asserts its mutation target exists, so none can pass vacuously), 17 for `db_guard`/`scan_repo` (working-tree vs `--archive` modes), 8 for the tsc classifier |
| `tools/audit/classify_tsc.py` (new) | strict tsc-diagnostic filter | replaces a broad `grep -v` allow-list; only "package/test-global not installed" is tolerated; relative-import errors, undefined names, syntax errors fail |
| `tools/audit/scan_repo.py`, `db_guard.py`, `bootstrap.sh` (new) | hygiene/compliance scan, DB safety guard, install helper | secrets / `.env` / keys / build dirs / `console.*` / third-party font-CDN-analytics hosts; refuse non-local or production-looking DBs and un-opted-in `migrate`; install only when a package index is reachable (exit 4 here) |
| `mobile/package.json` | added devDependencies `@types/jest`, `@types/node`, `react-test-renderer` | static reasoning: the test files use Jest globals and `Buffer` (type check would fail without `@types/jest`/`@types/node`), and `@testing-library/react-native` v12 requires `react-test-renderer` as a peer. **Unconfirmed until `npm install && npx tsc --noEmit && npx jest` is run** |
| `docs/RUN_BLOCKED_CHECKS.md` | rewritten | old guide mixed folders (it `cd`'d into `backend/` and then referenced `tools/audit/../../backend/...`). Now every step names its working directory, prerequisites, safe-DB rules, offline alternatives and a migration-drift plan |
| `docs/COMPLIANCE_REQUIREMENTS.md` (new) | records the owner's four rules (age at signup, self-hosted fonts, session logging, unsubscribe link) | recorded, **not implemented**: the age gate changes registration, outside this audit's scope. Fonts rule is already enforced by `scan_repo.py` |
| `tools/audit/README.md`, `docs/RELEASE_STATUS.md`, this file | updated | |
| `backend/profiles/models.py` | comment only (stale "INERT" note) | found during the manual review in section G; no behaviour change |

## C. Results (this sandbox)
| Command | Result | Exit |
|---|---|---|
| `bash tools/audit/run_all.sh` | PASS 9 · FAIL 0 · BLOCKED 8 · NOT_RUN 1 → "INCOMPLETE — NOT certified" | **2** |
| `bash tools/audit/selftest_run_all.sh` | 19/19 cases behave as required | **0** |
| `python3 -m unittest discover -s tools/audit/tests` | 56 tests OK | **0** |
| `python3 tools/audit/run_media_harness.py` | **EXECUTED — PASS** 35/35 (real Pillow 12.1.1; project pins 11.0.0) | 0 |
| `node tools/audit/run_ts_tests.js …` | **EXECUTED — PASS** 35/35, shim runner, **not Jest** | 0 |
| `python3 tools/audit/check_migrations.py` | **STATICALLY VERIFIED** — 8 apps, no inconsistency, nothing uninterpreted | 0 |
| `python3 tools/audit/scan_repo.py` | no secrets / `.env` / build dirs / `console.*` / third-party font-CDN-analytics hosts | 0 |
| `bash tools/audit/bootstrap.sh` | BLOCKED: PyPI / npm registry not reachable | **4** |
| `manage.py check`, `makemigrations --check --dry-run`, `showmigrations`, `pytest` (127 test functions), `migrate` on a fresh DB, HTTP permission/integration tests | **BLOCKED** (no Django, no PostgreSQL, no network) — `WRITTEN — NOT EXECUTED` | n/a |
| `npm ci` | **NOT RUN** — no `package-lock.json` exists and it can only be generated with network access | n/a |
| `npx tsc --noEmit`, `npx jest --runInBand` (incl. `AuthContext.test.tsx`), Expo run, emulator | **BLOCKED** (no `node_modules`) | n/a |

Mobile checks requested in the brief: `AuthContext.test.tsx` wraps `AuthProvider` in `QueryClientProvider` — **STATICALLY VERIFIED** (not run). `decodeUserId.test.ts` **fails when the old defect is re-introduced** —
**EXECUTED**: selftest case "JWT decode bug re-introduced (naive atob)" → `run_all.sh` exit 1, shim test FAIL (shim, not Jest).

## D. Statically verified only (no runtime proof)
Model↔migration consistency (v2 checker, mutation-tested by 26 defects) · serializer/route boundary scripts · hygiene scan · TS transpile + strict diagnostic classification (types **not** verified) · `package.json` dependency reasoning.

## E. New issues found in this round
1. **0.5.1 `run_all.sh` could report success while failing** (pipes into `tail`, `|| true`) — fixed (selftest-proven).
2. **`tsc` 6 rejects `moduleResolution=node10`** (`TS5107`); the old runner ignored it — fixed by version detection.
3. **`mobile/package.json` lacked `@types/jest`, `@types/node`, `react-test-renderer`** — added (unconfirmed until npm runs).
4. **Version-compatibility risk, not verified:** `djangorestframework-simplejwt 5.3.1` and `django-cors-headers 4.4.0` pre-date their official Django 5.1 support entries; they usually work but only `pytest` can confirm.
5. **No `package-lock.json`** → `npm ci` impossible until `npm install` is run once with network and the lock committed.
6. Owner compliance rules (age gate, session log, unsubscribe) are **not implemented** — see `COMPLIANCE_REQUIREMENTS.md`.

## F. DECISION: **NOT READY — BLOCKERS REMAIN**
Blockers: Django `check`, `makemigrations --check`, `showmigrations`, the 127-function pytest suite, migrations applied to a fresh PostgreSQL, real Jest/`tsc --noEmit`, Expo run and the end-to-end path were **not executed**.
Re-run on a machine with network: `docs/RUN_BLOCKED_CHECKS.md`; **READY FOR 0.6 requires `bash tools/audit/run_all.sh` to exit 0.**

## G. Manual code review (a review, NOT a test — nothing here was executed)
Because pytest cannot run here, I read these files line by line for authorization/logic defects: `follows/services.py`, `follows/views.py`, `profiles/public_views.py`,
`profiles/views.py`, `profiles/permissions.py`, `profiles/serializers.py`, `posts/views.py`, `engagement/views.py`, `safety/views.py`, `notifications/views.py`,
`notifications/services.py`, `media/services.py`, `media/signals.py`, `core/exceptions.py`, `accounts/models.py`, `profiles/models.py`.
**Result: no authorization defect found** (every write resolves the actor from `request.user`; id-in-URL routes are scoped by queryset; block/visibility rules are applied in one module). Absence of a found bug is **not** proof — only the un-run tests can confirm.
Observations (decisions, not proven defects; **none were changed**):
1. Follow / block / accept / decline share one throttle bucket (`follow_write`, 120/h per user).
2. After a block, the two users' existing likes/comments on each other's posts remain stored (hidden from view, but still counted in `like_count`/`comment_count`).
3. If the DB insert fails after the image files were written, the files are orphaned (`cleanup_orphan_images` only removes rows + their files).
4. `UserManager.get_by_natural_key` uses `email__iexact`; it would raise `MultipleObjectsReturned` only if case-variant duplicate users ever existed (impossible via the API; possible only through legacy imports).
5. Cursor pagination orders by `created_at` only; rows with identical timestamps could be skipped/duplicated at page boundaries (microsecond timestamps make this unlikely).
6. Pending follow requests stay pending if the target later switches from private to public (documented in ADR-0021).
7. Throttle counters use the per-process default cache until a shared cache (Redis) is configured.
The only edit made from this review: a stale comment in `profiles/models.py` (it still said `is_private_account` was "INERT"; it has driven visibility since 0.2). No behaviour changed.

---
# Original 0.5.1 report (kept for history)
> Correction: where the text below refers to `tools/audit/run_all.sh` behaviour or "three tools", it describes the 0.5.1 version, which could mask failures (see E.1).

# VEYA 0.5 — Execution, Migration & Regression Audit
Date: 2026-10-27 · Input: `veya-0_5-django-rn.zip` (backup kept as `BACKUP_veya-0_5-django-rn.zip`) · Output: `veya-0_5_1-audit-django-rn.zip`

Status vocabulary: **EXECUTED — PASS / FAIL**, **STATICALLY VERIFIED**, **WRITTEN — NOT EXECUTED**, **BLOCKED**.

## 1. Execution environment
| Item | Result |
|---|---|
| Python | 3.12.3 (system) |
| Django / DRF / SimpleJWT / pytest / pytest-django / psycopg / django-environ / corsheaders | **not installed** — BLOCKED (no network: `pip download` finds no distribution) |
| Pillow | 12.1.1 installed (project pins 11.0.0) |
| PostgreSQL / Docker | **not available** — BLOCKED |
| Node / npm | v22.22.2 / 10.9.7; every `npm` command errors with a config problem in the sandbox's own `~/.npmrc` ("config prefix cannot be changed"), and `pip` shows no package index is reachable, so installs are BLOCKED either way |
| TypeScript compiler | `tsc` 6.0.3 available (project pins ~5.6.3) |
| Jest, jest-expo, Expo CLI, emulator/device | **not available** — BLOCKED |

## 2–4. Django check / migrations / backend pytest
| Check | Status |
|---|---|
| `manage.py check` | **BLOCKED** (no Django) |
| `makemigrations --check --dry-run` | **BLOCKED** |
| `showmigrations` | **BLOCKED** |
| Backend pytest — 127 test functions written (≈150 cases) | **WRITTEN — NOT EXECUTED**: 0 passed, 0 failed, 0 skipped. No claim of success is made. |
| Model ↔ hand-written migration consistency (fields, FK targets, options, indexes, constraints, dependency graph, cycles) | **STATICALLY VERIFIED** — `tools/audit/check_migrations.py` (a first run produced false alarms from my own checker — inherited `AbstractBaseUser` fields, per-file dependencies, `swappable_dependency` — which I fixed in the checker; the project files were not changed). **Mutation-tested**: 4 seeded defects (missing dependency, wrong index name, wrong max_length, extra model field) were all detected. This does **not** replace Django's autodetector. |
| Other static checks | `ast.parse` on 111 backend files: STATICALLY VERIFIED. Local-import resolution: 0 missing. `verify_boundaries.py`: EXECUTED — PASS. Route names used by tests exist (the one "missing" name, `profile-detail`, is intentionally absent — that test asserts `NoReverseMatch`). Test fixtures resolve (only `@pytest.mark.parametrize` names remain, as expected). |

## 5. Security — what was actually executed
**EXECUTED — PASS (35/35)**, `tools/audit/run_media_harness.py`: the real `media/processing.py` and `media/signing.py` run with real
Pillow (Django/DRF stubbed) against valid and hostile inputs:
* JPEG/PNG/WEBP accepted; RGBA/palette/CMYK/16-bit inputs handled; post ≤1600 px (thumb ≤400), avatar ≤512 px (thumb ≤128).
* EXIF text, camera tags and a GPS IFD are removed from the stored bytes; EXIF orientation is applied first.
* Data appended after a JPEG and a crafted PNG text chunk do **not** survive re-encoding; original bytes are never stored.
* Rejected: text/HTML/SVG-with-script disguised as images, GIF, BMP, TIFF, empty file, truncated JPEG, random bytes,
  over-size, over-pixel-limit, an invalid `kind`, and a **real 900-megapixel decompression bomb** that fits in a few KB.
* Signed URLs: valid round-trip, tamper/other-id/garbage rejected, previous bucket valid, expired bucket rejected, deterministic within a bucket.
* **Mutation-tested**: removing the pixel guard, EXIF stripping/orientation, or allowing GIF each made the right tests fail
  (note: with the pixel guard removed the bomb is still stopped by Pillow's own `DecompressionBombError` — defence in depth).

**STATICALLY VERIFIED (config review, not runtime):** JWT only (`DEFAULT_AUTHENTICATION_CLASSES`), default permission `IsAuthenticated`,
JSON renderer only, access 15 min / refresh 30 d with rotation + blacklist (`token_blacklist` installed), scoped throttles on
register/login/refresh/post/follow/search/report/comment/like/upload, secrets read from the environment only, prod hardening
(SSL redirect, HSTS, secure cookies), CORS origins from env (React Native needs none), no `.env`/key files in the archive,
no `console.*` calls in the mobile source, no hard-coded secrets (regex scan), the only mobile env value is the public API base URL.

**NOT verified at runtime (BLOCKED):** every permission/ownership/visibility rule over HTTP (private accounts, blocks, reports,
admin), throttling behaviour, CSRF/CORS behaviour, DB constraints, media serving, notification scoping. These live in the 127 un-run tests.

## 6. Mobile
| Check | Status |
|---|---|
| `npm ci` / `npm install` | **BLOCKED** (sandbox npm error / no package index; also **no `package-lock.json`** is shipped, so `npm ci` would fail even with network) |
| `tsc` syntax emit over `src/` | EXECUTED — emits (type errors from uninstalled packages are expected; **types NOT verified**) |
| Pure tests: validators, pagination, post/comment validation, notification text, image validation, JWT decoding — 35 `it` cases | **EXECUTED — PASS (35/35)** with a ~40-line `describe/it/expect` shim on the compiled source, **not Jest**. Mutation-tested: the original naive-`atob` bug makes the JWT test fail. |
| `AuthContext.test.tsx` (React Native renderer) | **BLOCKED** (+ defect fixed, see §7) |
| Screens, navigation, secure storage, token refresh, loading/error states, image picking | **WRITTEN — NOT EXECUTED** (no RN runtime) |
| Emulator / device run | **BLOCKED** |

## 7. Integration (11-step path) — **BLOCKED**
Register → login → profile → post → follow/request → upload image → like/comment → block → report → notification → logout/login.
Needs Django + PostgreSQL + the app running; none available. Each step has backend tests written, none executed.

## 8. Defects found and fixed in this audit
| # | Where | Defect | Evidence | Fix |
|---|---|---|---|---|
| A1 | `mobile/package.json` | `"test": "jest"` but **no Jest configuration** (no `jest-expo` preset) → `npm test` would fail on TS/JSX/Expo modules | read `package.json`; no `jest.config.*`, no `jest` key | added `"jest": {"preset": "jest-expo"}` |
| A2 | `mobile/src/__tests__/AuthContext.test.tsx` | `AuthProvider` has called `useQueryClient()` since 0.2, but the test renders it without `QueryClientProvider` → would throw "No QueryClient set" | code read | wrapped in `QueryClientProvider`; removed unused imports |
| A3 | `mobile/src/__tests__/decodeUserId.test.ts` | the url-safe-base64 assertion ended in `|| true` and could not fail; the payload didn't force `-`/`_` | read; **mutation test** with the original bug passed before the fix | payload now forces both characters, guarded by assertions; verified it fails against naive `atob` |
| A4 | docs / dev setup | a phone on the LAN gets `DisallowedHost` unless `ALLOWED_HOSTS` includes the dev machine (`.env.example` only lists localhost) | settings review | documented in `RUN_BLOCKED_CHECKS.md` |

No backend source file needed a change. Not claimed: that the backend works — it is untested.

## 9. Not tested
Everything marked BLOCKED above, plus: iOS/Android runtime behaviour, real PostgreSQL behaviour of the `\S` regex CHECK constraints
and partial indexes, concurrency (like/follow races), Pillow 11.0.0 specifically (harness ran on 12.1.1), Expo SDK 52 compatibility of
`expo-image-picker ~16.0.3`, performance, backups, monitoring.

## 10. Status per release
| Release | Backend code | Backend tests | Migrations | Mobile code | Mobile tests |
|---|---|---|---|---|---|
| 0.1 auth/profile | WRITTEN — NOT EXECUTED | WRITTEN — NOT EXECUTED | STATICALLY VERIFIED (consistency only) | WRITTEN — NOT EXECUTED | pure validators EXECUTED — PASS; AuthContext BLOCKED |
| 0.2 posts/follows/feed | WRITTEN — NOT EXECUTED | WRITTEN — NOT EXECUTED | STATICALLY VERIFIED | WRITTEN — NOT EXECUTED | pagination/post validation EXECUTED — PASS |
| 0.3 blocks/reports/likes/comments | WRITTEN — NOT EXECUTED | WRITTEN — NOT EXECUTED | STATICALLY VERIFIED | WRITTEN — NOT EXECUTED | comment validation EXECUTED — PASS |
| 0.4 images | **image pipeline + signing: EXECUTED — PASS** (Pillow level); views/attach rules WRITTEN — NOT EXECUTED | WRITTEN — NOT EXECUTED | STATICALLY VERIFIED | WRITTEN — NOT EXECUTED | image validation EXECUTED — PASS |
| 0.5 notifications | WRITTEN — NOT EXECUTED | WRITTEN — NOT EXECUTED | STATICALLY VERIFIED | WRITTEN — NOT EXECUTED | notification text EXECUTED — PASS |

## 11. Files changed
`mobile/package.json` · `mobile/src/__tests__/AuthContext.test.tsx` · `mobile/src/__tests__/decodeUserId.test.ts` ·
new: `tools/audit/{README.md,run_all.sh,run_media_harness.py,check_migrations.py,run_ts_tests.js}` ·
`docs/AUDIT_0.5.md` · `docs/RUN_BLOCKED_CHECKS.md` · `docs/RELEASE_STATUS.md` (audit section).

## 12. DECISION: **NOT READY — BLOCKERS REMAIN**
The mandatory checks — Django `check`, `makemigrations --check`, the backend pytest suite, `jest`, and the end-to-end path —
were not executable here. Passing the offline checks above lowers risk (the image pipeline is genuinely verified at the Pillow level)
but proves nothing about the Django layer, where all the authorization logic lives. Run `docs/RUN_BLOCKED_CHECKS.md` and send the output.
