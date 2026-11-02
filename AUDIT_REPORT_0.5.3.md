# VEYA 0.5.3 — Final audit report
Input: `veya-0_5_2_1-closure-and-compliance-plan.zip` (kept as `BACKUP_veya-0_5_2_1.zip`) · 2026-10-30 · **Decision: NOT READY — BLOCKERS REMAIN**
Statuses: EXECUTED — PASS/FAIL · STATICALLY VERIFIED · WRITTEN — NOT EXECUTED · BLOCKED · NOT_RUN. Nothing is reported as passed unless it ran.

## 1. Environment (re-verified this session)
Python 3.12.3 · Node 22.22.2 · tsc 6.0.3 · Pillow 12.1.1. `curl https://pypi.org/...` and `https://registry.npmjs.org/expo` → HTTP code 000 (no network). Django, DRF, SimpleJWT, django-environ, cors-headers, psycopg, pytest, pytest-django **not installed**; no PostgreSQL/Docker/Jest/Expo/emulator.

## 2. Phase 1 — audit tooling
* **Full run of the tools** (`run_all.sh`, `collect_report.sh`, `verify_archive.sh`): finished in ~11–13 s each, exit 2 — **no hang, no timeout, no crash**. Exit 2 = BLOCKED/NOT_RUN rows only. (A `time: not found` seen once was my own `sh` invocation, not a tool defect.) The self-test takes ~6 min and exceeded this sandbox's 300 s per-command limit and background jobs do not survive between commands, so it was run in 3 batches (`SELFTEST_RANGE`); the limit is the sandbox, not the code.
* **Exit codes preserved**: 0 all passed · 1 a real failure · 2 nothing failed but checks blocked/not run (verified by 27 injection cases).
* **Defects found in the tools and fixed (no check was weakened):**
  1. repo-hygiene scan failed on developer leftovers (`.pytest_cache`, git-ignored `backend/.env`) — would have produced false FAILs on the user's machine → two modes (working tree / `--archive`) and `verify_archive.sh`.
  2. the tools' own unit tests assumed a clean project copy (a developer's `.env` would fail them) and a hard-coded app count (8 → 10) → made self-contained / derived from disk.
  3. `mask_secrets.py` did not mask `Bearer …` tokens or `Authorization`/`Cookie` headers (**found by the injection test: a token leaked into a report**) and ignored `backend/.env` → fixed + unit tests; now masks secret-looking values from `backend/.env` and the environment, passwords in URLs, JWTs, Bearer/Basic, Authorization/Cookie headers.
  4. `collect_report.sh`: a failing generator could produce a truncated report silently → now writes a `.partial` file, requires the RESULT section and exits 3 loudly; owner-only umask on logs/reports.
  5. selftest copy lacked the root `.gitignore`; selftest gained batching (`SELFTEST_RANGE`).
* **Added**: `check_python_static.py`, pure-logic backend tests wired into `run_all.sh`, secret/hygiene coverage for `audit_report_*.txt`, root `.gitignore`.
* **Docs**: `RELEASE_STATUS.md` rewritten as one non-contradictory source of truth (old per-release "scope/NOT run/first commands" blocks removed); `AUDIT_0.5.md` kept as history with a pointer; `COMPLIANCE_PLAN.md` updated with real status. **No migration was deleted or regenerated.**

## 3. Phase 2 — compliance requirements (implemented in code, ADR-0026)
| Rule | What was built | Status |
|---|---|---|
| Age at signup | `date_of_birth` required at signup; server compares with `VEYA_MINIMUM_AGE`; only birth **year+month** stored (`AgeRecord`); neutral error, no threshold leak; same-e-mail cooldown; `POST /auth/age/` + production read-only gate for legacy accounts; mobile DD/MM/YYYY entry + blocking age screen | arithmetic **EXECUTED — PASS** (6) · mobile date parsing **EXECUTED — PASS** (8) · API/DB/screens **WRITTEN — NOT EXECUTED** (20 pytest functions incl. allowed/rejected/boundary/retry-bypass/enforcement/no-leak) |
| Local fonts | verified: no custom fonts anywhere (no `expo-font`, `fontFamily`, font files, external hosts) — **nothing added**, no licences involved | **STATICALLY VERIFIED** + enforced by scan |
| Security/session logs | `securitylog`: login success/failed, logout, rejected logout, failed refresh; truncated IP, coarse client label; no credentials/tokens/typed e-mail; purge command; read-only admin; own-events endpoint; log redaction on all handlers | helpers + redaction **EXECUTED — PASS** (15) · DB/API **WRITTEN — NOT EXECUTED** (13 functions) |
| Marketing unsubscribe | `mailing`: opt-in preference, signed link (GET shows page, POST unsubscribes, RFC 8058 one-click), hashed suppression list, marketing vs transactional policy, senders **disabled** | tokens + policy **EXECUTED — PASS** (12) · endpoints **WRITTEN — NOT EXECUTED** (19 functions). **NOT ACTIVATED — no e-mail is sent** |
Existing tests updated for the new signup field (`test_auth.py`).

## 4. Phase 3 — real tests
| Item | Result |
|---|---|
| Django / PostgreSQL / `check` / `makemigrations --check` / `showmigrations` / `migrate` / `pytest` (179 Django-dependent functions) / HTTP integration / privacy-permission-login-age-unsubscribe tests over the API | **BLOCKED** — no network, Django, PostgreSQL |
| Mobile `npm ci` | **NOT_RUN** — no lock file; cause: it can only be generated with network access (`npm install`, then commit) |
| `npx tsc --noEmit`, Jest, app run | **BLOCKED** — no `node_modules` |
| Safety | no migration was applied anywhere; `db_guard.py` (unit-tested) refuses non-local hosts, production-looking names and `migrate` outside `veya_audit*`/`*_test` |
Executed instead (clearly *not* substitutes): backend pure tests 34/34 · image pipeline 35/35 · mobile shim 43/43 · tools 69/69 · injection self-test 27/27 · static checks above.

## 5. Residual risks
Django-layer code (age gate, security log, mailing, and all of 0.1–0.5) is unexecuted — expect small fixes on first `pytest` · cooldown/throttles per-process without Redis · self-declared age is bypassable · SimpleJWT/cors-headers vs Django 5.1 unverified · mobile dev-dependencies added in 0.5.2 unconfirmed until `npm install` · purge job and retention scheduling not set up · unsubscribe link TTL 365 days is a placeholder.

## 6. Decisions needing the owner / counsel
(1) **Minimum age** per target market (and whether parental-consent flows are needed) · (2) whether self-declaration is sufficient or stronger age assurance is expected · (3) retention for security logs (90 days is only a proposal) and what survives account deletion · (4) opt-in vs opt-out for marketing per market, unsubscribe link lifetime, sender postal address, e-mail provider · (5) CNDP/other regulator notices and cross-border transfer authorisations for your hosting · (6) privacy policy, terms/EULA, acceptance record · (7) account deletion/export design and legal retention exceptions · (8) minors safeguards and abuse-reporting duties. **Nothing here is a claim of legal compliance.**

## 7. Re-run commands
```bash
cd /path/to/veya2
bash tools/audit/run_all.sh;  echo $?                       # 0 required
( cd backend && python -m pytest -q -ra );  echo $?          # needs docs/RUN_BLOCKED_CHECKS.md steps 1-3
bash tools/audit/collect_report.sh                          # one masked report file to send back
bash tools/audit/selftest_run_all.sh                        # ~6 min; SELFTEST_RANGE=1-10 for a batch
bash tools/audit/verify_archive.sh path/to/archive.zip
```

## 8. Changed files vs `veya-0_5_2_1-closure-and-compliance-plan.zip`
15 new, 37 modified.
**New:** `.gitignore`, `backend/accounts/age.py`, `backend/accounts/migrations/0002_agerecord.py`, `backend/mailing`, `backend/securitylog`, `backend/tests/pure`, `backend/tests/test_age_gate.py`, `backend/tests/test_mailing.py`, `backend/tests/test_security_log.py`, `docs/adr/0026-compliance-implementation.md`, `mobile/src/__tests__/age.test.ts`, `mobile/src/auth/age.ts`, `mobile/src/auth/screens/AgeGateScreen.tsx`, `mobile/src/mailing`, `tools/audit/check_python_static.py`
**Modified:** `backend/.env.example`, `backend/accounts/models.py`, `backend/accounts/serializers.py`, `backend/accounts/urls.py`, `backend/accounts/views.py`, `backend/config/settings/base.py`, `backend/config/settings/prod.py`, `backend/config/urls.py`, `backend/profiles/permissions.py`, `backend/profiles/serializers.py`, `backend/profiles/validators.py`, `backend/scripts/verify_boundaries.py`, `backend/tests/test_auth.py`, `docs/API.md`, `docs/COMPLIANCE_PLAN.md`, `docs/COMPLIANCE_REQUIREMENTS.md`, `docs/DATABASE_SCHEMA.md`, `docs/RUN_BLOCKED_CHECKS.md`, `docs/SECURITY_DECISIONS.md`, `mobile/app.json`, `mobile/package.json`, `mobile/src/auth/AuthContext.tsx`, `mobile/src/auth/screens/SignUpScreen.tsx`, `mobile/src/navigation/RootNavigator.tsx`, `mobile/src/profile/api.ts`, `mobile/src/profile/hooks/useProfile.ts`, `mobile/src/profile/screens/ProfileScreen.tsx`, `mobile/src/profile/types.ts`, `tools/audit/README.md`, `tools/audit/collect_report.sh`, `tools/audit/mask_secrets.py`, `tools/audit/run_all.sh`, `tools/audit/scan_repo.py`, `tools/audit/selftest_run_all.sh`, `tools/audit/tests/test_check_migrations.py`, `tools/audit/tests/test_db_guard_and_scan.py`, `tools/audit/tests/test_mask_secrets.py`

## 9. Addendum — phone / cloud path (0.5.3.1)
Owner works from a phone only. Added `tools/audit/cloud_run.sh`, `cloud/audit.yml` (GitHub Actions: private repo, Postgres service container, no repository secrets, results as masked report + logs + generated `package-lock.json`) and `docs/RUN_FROM_PHONE.md`.
* **Executed here:** script syntax; `--check` (exit 0); unknown option (exit 2); no-network path (exit 4, nothing installed); workflow-structure and no-secrets tests (6 tests, mutation-checked); tools unit tests 69/69.
* **NOT executed anywhere:** the install + run path on GitHub/Codespaces/Cloud Shell — **WRITTEN — NOT EXECUTED**. Free-tier limits of these services are from general knowledge and must be checked.
* **Defect found and fixed:** a short throw-away DB password (`veya`) made `mask_secrets.py` replace every "veya" in a report with `***` (garbled report). Literal masking now needs 8+ characters; short passwords are still masked in URL/KEY=value context; docs use an 8+ character throw-away password.
* Decision unchanged: **NOT READY — BLOCKERS REMAIN** (needs a real run with exit code 0).
