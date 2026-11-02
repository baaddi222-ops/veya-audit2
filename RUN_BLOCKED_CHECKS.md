> **أعمل من الهاتف فقط؟ ← `docs/RUN_FROM_PHONE.md`** (GitHub Actions من المتصفح، بلا طرفية).
> Use passwords of 8+ characters even for throw-away databases: shorter ones cannot be masked safely in shared reports.

# QUICK PATH — close the audit blockers on a machine WITH internet (run everything from `PROJECT_ROOT`)

`PROJECT_ROOT` is the folder that contains `backend/`, `mobile/`, `docs/`, `tools/`. Use Linux, macOS, WSL, or Git Bash on Windows (`run_all.sh` is a bash script).
Requirements: Python 3.12, Node 20+, Docker (for a throw-away PostgreSQL). Nothing below touches production.

```bash
# 0) go to the project root
cd /path/to/veya2

# 1) throw-away PostgreSQL (name starts with veya_audit so the safety guard accepts it)
docker run -d --name veya-audit-db -e POSTGRES_USER=veya -e POSTGRES_PASSWORD=audit_pw_8f3k2x -e POSTGRES_DB=veya_audit -p 5432:5432 postgres:16

# 2) install the toolchains (creates backend/.venv and mobile/node_modules; first time also creates mobile/package-lock.json)
bash tools/audit/bootstrap.sh
source backend/.venv/bin/activate            # Windows Git Bash: source backend/.venv/Scripts/activate  (and run the next steps with PYTHON=python)

# 3) environment for the backend (exported in this shell — no .env file needed, nothing is written to disk)
export DJANGO_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(50))')"
export DATABASE_URL="postgresql://veya:audit_pw_8f3k2x@localhost:5432/veya_audit"
export ALLOWED_HOSTS="127.0.0.1,localhost"
export DJANGO_SETTINGS_MODULE="config.settings.dev"
# (dev defaults: VEYA_MINIMUM_AGE=16 placeholder, VEYA_ENFORCE_AGE_GATE=False. Production REQUIRES VEYA_MINIMUM_AGE.)

# 4) THE audit — exit 0 only when every check ran and passed (1 = a failure, 2 = something could not run)
bash tools/audit/run_all.sh;  echo "run_all exit code: $?"

# 5) pytest on its own, from the project root (a sub-shell; the backend's pytest.ini lives in backend/)
( cd backend && python -m pytest -q -ra );  echo "pytest exit code: $?"

# 5b) (maintainers) verify a release zip exactly as a recipient gets it
bash tools/audit/verify_archive.sh /path/to/archive.zip

# 6) one file to send back (secrets masked; exit code = run_all.sh's)
bash tools/audit/collect_report.sh           # writes audit_report_<timestamp>.txt in PROJECT_ROOT
```
**PowerShell equivalents** (no bash needed for pytest; use WSL/Git Bash for `run_all.sh`):
`$env:DJANGO_SECRET_KEY="<long random>"; $env:DATABASE_URL="postgresql://veya:audit_pw_8f3k2x@localhost:5432/veya_audit"; $env:DJANGO_SETTINGS_MODULE="config.settings.dev"; Push-Location backend; python -m pytest -q -ra; Pop-Location`

**If anything FAILS — protocol (do not improvise):**
1. Do **not** delete or regenerate migrations and do **not** loosen permission rules to make a test pass.
2. Run `bash tools/audit/collect_report.sh` and send me the file.
3. For a failing test I will show the evidence (assertion + code path) and propose the smallest fix, with the new/updated test, **before** changing anything.
4. For `makemigrations --check` differences follow §4 below (plan first; applied migrations are never edited).

**The release is NOT ready until `bash tools/audit/run_all.sh` exits 0 on the connected machine** (and the manual walkthrough in §7 passes).
Cleanup when finished: `docker rm -f veya-audit-db`.

---
# Running the checks that were BLOCKED in the authoring sandbox

**Why they were blocked (verified 2026-10-27):** the sandbox has Python 3.12.3, Node 22, Pillow and `tsc`, but **no network**
(`curl https://pypi.org` and `https://registry.npmjs.org` both return HTTP code 000; `pip download django` finds nothing; `npm view`
fails with `npm error network`), no PostgreSQL/Docker, no Jest/Expo, no emulator. So Django, DRF, pytest, Jest and the app could not be
installed or run. **No blocked check has been claimed as passed.**

## 0. Conventions (read once)
* `PROJECT_ROOT` = the folder that contains `backend/`, `mobile/`, `docs/`, `tools/` (the unzipped `veya2/`).
* Every command below states the folder to run it from. Commands are for **Linux/macOS bash**; Windows equivalents are given where they differ.
* Nothing here touches production. Use a **throw-away local PostgreSQL** only. `tools/audit/db_guard.py` refuses non-local hosts,
  production-looking names, and `migrate` on anything not named `veya_audit*` / `*_test` without `VEYA_AUDIT_ALLOW_MIGRATE=1`.

| # | Check | Run from | Needs |
|---|---|---|---|
| 1 | Offline audit (already works anywhere) | `PROJECT_ROOT` | python3, Pillow, node, tsc |
| 2 | Toolchain install | `PROJECT_ROOT` | network (PyPI + npm) |
| 3 | Throw-away PostgreSQL | any | Docker (or a local PostgreSQL) |
| 4 | Django check / migrations / pytest | `PROJECT_ROOT/backend` | step 2 + 3 |
| 5 | Mobile tsc / Jest | `PROJECT_ROOT/mobile` | step 2 |
| 6 | Whole audit again | `PROJECT_ROOT` | steps 2–5 |
| 7 | Manual end-to-end | emulator/device | backend running |

## 1. Offline audit (no installs)
```bash
cd PROJECT_ROOT
bash tools/audit/run_all.sh          # exit 0 = all checks ran & passed | 1 = a check FAILED | 2 = nothing failed but some checks BLOCKED/NOT_RUN
bash tools/audit/selftest_run_all.sh # proves run_all.sh really fails (exit 1) on 15 injected defects, stays 2 (never 0) when tools are missing, and does not false-alarm on a git-ignored `.env` or pytest caches
python3 -m unittest discover -s tools/audit/tests -v   # 56 tests of the audit tools themselves
```
Exit code **2 means "not certified"**, never "good". Only exit 0 means every check (including the real Django/pytest/Jest ones) ran and passed.

## 2. Install toolchains (needs internet)
```bash
cd PROJECT_ROOT
bash tools/audit/bootstrap.sh                  # backend venv + mobile node_modules; exits 4 = BLOCKED (no network)
# or by hand:
cd backend && python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install --upgrade pip && pip install -r requirements-dev.txt
cd ../mobile && npm install                    # FIRST time only: creates package-lock.json -> commit it. Afterwards: npm ci
```
`npm ci` needs `mobile/package-lock.json`, which is **not shipped yet** (it can only be generated with network access).

**No internet on the target machine?** On a networked machine run `pip download -r backend/requirements-dev.txt -d wheelhouse`
and `npm ci` once, copy `wheelhouse/` and `mobile/node_modules/` over, then `pip install --no-index --find-links wheelhouse -r backend/requirements-dev.txt`.
Or use CI / a dev container that has network access. The offline tools in `tools/audit/` are **not** substitutes for these checks.

## 3. Throw-away PostgreSQL
```bash
docker run -d --name veya-audit-db -e POSTGRES_USER=veya -e POSTGRES_PASSWORD=audit_pw_8f3k2x -e POSTGRES_DB=veya_audit -p 5432:5432 postgres:16
```

## 4. Backend checks — run from `PROJECT_ROOT/backend` (venv active)
```bash
cd PROJECT_ROOT/backend
cp .env.example .env          # Windows: copy .env.example .env      (.env is git-ignored; never commit or zip it)
# edit .env:  DJANGO_SECRET_KEY=<long random string>
#             DATABASE_URL=postgresql://veya:audit_pw_8f3k2x@localhost:5432/veya_audit
#             ALLOWED_HOSTS=127.0.0.1,localhost      (+ your LAN IP, or * for DEV ONLY, if a phone must reach it)
python ../tools/audit/db_guard.py                 # exit 0 = target is local/throw-away
python manage.py check
python manage.py makemigrations --check --dry-run # must print "No changes detected"
python manage.py showmigrations                   # nothing should be applied yet
python -m pytest -q                               # 127 test functions (~150 cases); pytest-django creates/destroys test_veya_audit itself
export VEYA_AUDIT_ALLOW_MIGRATE=1                 # Windows: set VEYA_AUDIT_ALLOW_MIGRATE=1
python ../tools/audit/db_guard.py --for-migrate   # name must be veya_audit* or *_test
python manage.py migrate                          # applies all 10 migrations to the throw-away DB
python scripts/verify_boundaries.py               # static checks, also runnable from here
python ../tools/audit/check_migrations.py         # static checker (path-independent)
```
**If `makemigrations --check` reports changes — do not delete or regenerate blindly.**
1. Save the output and run `python manage.py makemigrations --dry-run -v 3` to see the exact operations.
2. Run `python manage.py showmigrations`. If **no environment has ever applied** these migrations, the hand-written file may be edited
   to match (or replaced by generated output for that app only) — the risk is losing intentional hand edits and changing migration names/dependencies.
3. If **any** database has applied them, never edit them: add a **new** migration (`makemigrations`) instead; editing applied history breaks other environments.
4. Re-run `check_migrations.py`, `makemigrations --check`, `pytest`.

## 5. Mobile checks — run from `PROJECT_ROOT/mobile`
```bash
cd PROJECT_ROOT/mobile
cp .env.example .env     # EXPO_PUBLIC_API_BASE_URL=http://<your-LAN-IP>:8000/api   (Android emulator: http://10.0.2.2:8000/api)
npm ci                   # only once package-lock.json exists (see §2); otherwise npm install
npx tsc --noEmit         # real type check (needs the dev dependencies incl. @types/jest, @types/node)
npx jest --runInBand     # real Jest incl. src/__tests__/AuthContext.test.tsx (QueryClientProvider is in place)
npx expo start           # then scan the QR with Expo Go / press a for Android emulator
```
If Jest cannot parse a dependency (`SyntaxError: Cannot use import statement`) add that package to `transformIgnorePatterns` in the `jest` block of `package.json` — unverified risk.

## 6. Run the whole audit again (from `PROJECT_ROOT`)
```bash
cd PROJECT_ROOT && bash tools/audit/run_all.sh
```
When the real checks are installed the BLOCKED rows turn into real PASS/FAIL rows. **READY FOR 0.6 requires exit code 0.**

## 7. Manual end-to-end (emulator/device, backend running)
Use two accounts (A, B). Expected result in brackets.
1. Register A → [signed in, onboarding asks for a username].  2. Log out, log in → [session restored].  3. Edit profile → [saved; invalid username rejected].
4. A creates a post → [appears in A's feed].  5. B follows A (A is private) → [B sees "Requested"; A sees a request + notification]; A accepts → [B sees A's posts, gets "accepted" notification].
6. A uploads a photo post → [image shows; a GIF/oversized file is rejected with a clear message].  7. B likes + comments → [counts update; A notified once per like].
8. B blocks A → [A's profile/posts/comments vanish for B and vice-versa; follows removed; notifications between them deleted].  9. B reports a post → [“received”; repeating it does not error].
10. Open Alerts → [unread badge, tap marks read].  11. Log out/in → [no stale data from the previous account].
Also try as B: open A's post id directly, A's image URL without the signature, another user's notification id → [all 404/403, never data].

## 8. Never
Run migrations on production · commit `.env`, keys or service files · widen permissions to make a test pass · treat exit code 2 as success.
