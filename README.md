# tools/audit — offline audit tooling

| Tool | Purpose | Evidence kind |
|---|---|---|
| `run_all.sh` | Runs every check below + the real Django/pytest/Jest checks when installed. Per check: `PASS` / `FAIL` / `BLOCKED` / `NOT_RUN`. **Exit 0** = all ran & passed, **1** = something failed, **2** = nothing failed but something could not run (not certified). Never hides a child's exit code (no `tail`, no `|| true`). | — |
| `selftest_run_all.sh` | Failure-injection test of `run_all.sh`: 27 cases: 21 injected defects → exit 1 (incl. age-rule off-by-one, unchecked unsubscribe-token signature, removed JWT redaction), baseline + developer leftovers + 2 missing-tool cases → exit 2, a report that must mask `.env`/env secrets (exit 1, no leak) and a generator failure that must be loud (exit 3). Takes ~6 min; `SELFTEST_RANGE=1-10` runs a batch. | executed |
| `check_python_static.py` | Backend Python: every file parses, local imports resolve, no undefined names. | static |
| `check_migrations.py` | AST comparison of models vs hand-written migrations: types, every kwarg, defaults, choices, validators, FK targets, Meta ordering/indexes/constraints (Q-expressions normalised), inherited `AbstractBaseUser`/`PermissionsMixin` fields, dependency existence/cycles/cross-app coverage. Reports anything it cannot interpret as UNVERIFIED. **Not** Django's autodetector. | static |
| `classify_tsc.py` | Strict filter for `tsc` output without `node_modules`: tolerates only "package/test-global not installed"; real errors (syntax, undefined names, broken relative imports) fail. | static |
| `run_media_harness.py` | Runs the real `media/processing.py` + `media/signing.py` with real Pillow against ~35 valid/hostile inputs (Django stubbed). | executed |
| `run_ts_tests.js` | Runs the real pure-function `src/__tests__` files with a tiny `describe/it/expect` shim. **Not Jest.** | shim |
| `verify_archive.sh` | Extracts a release zip elsewhere, runs `scan_repo.py --archive` (strict) and `run_all.sh` on the extracted copy. Exit 0 only if both are clean/passing. | executed |
| `scan_repo.py` | Two modes: working tree (default, used by `run_all.sh`; tolerates git-ignored `.env`/caches/venv) and `--archive` (strict). Secrets, `.env`, keys, sqlite DBs, build dirs, `console.*` in mobile, third-party font/CDN/analytics/session-recording hosts. | static |
| `db_guard.py` | Refuses non-local / production-looking databases and un-opted-in `migrate`. | executed (unit-tested) |
| `collect_report.sh` | One command for a connected machine: runs `run_all.sh` and writes ONE masked text report (environment, results, logs, verdict). Exit code = `run_all.sh`'s. | — |
| `mask_secrets.py` | stdin→stdout filter that masks DB passwords, secret keys, tokens, JWTs (unit-tested). | executed |
| `cloud_run.sh` | One command for a CLOUD environment (GitHub Actions / Codespaces / Cloud Shell): installs deps, runs everything against a throw-away PostgreSQL, writes `cloud_out/` (masked report, full logs, `package-lock.json`, `SUMMARY.md`). `--check` prints the plan; `--start-db` starts postgres via docker. Exit = run_all's code, 4 = BLOCKED (no network), 5 = setup failed. **Success path not yet executed anywhere.** | — |
| `bootstrap.sh` | Creates the backend venv and installs mobile deps when a package index is reachable; exit 4 = BLOCKED. | — |
| `tests/` | 69 `unittest` tests of the tools themselves (26 checker defects, 20 db_guard/scan, 8 classifier, 9 secret masking incl. backend/.env literals and Bearer/Cookie headers). `python3 -m unittest discover -s tools/audit/tests` | executed |

Statuses used in the docs: **EXECUTED — PASS/FAIL**, **STATICALLY VERIFIED**, **WRITTEN — NOT EXECUTED**, **BLOCKED**.
Step-by-step instructions for everything that needs Django/PostgreSQL/npm: `docs/RUN_BLOCKED_CHECKS.md`.
