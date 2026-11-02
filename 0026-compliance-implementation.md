# ADR-0026: Compliance features in 0.5.3 (age gate, security log, e-mail unsubscribe)
Date: 2026-10-30 · Status: Accepted by the owner's instruction; **legal parameters undecided** · Release: VEYA 0.5.3
Not legal advice. Every value marked **[COUNSEL]** is a project-policy placeholder, not a statement of what any law requires.

## Age at signup
* `POST /api/auth/register/` requires `date_of_birth`. The server compares it with **`settings.VEYA_MINIMUM_AGE`** (policy value; dev default 16 **[COUNSEL]**; **production fails to start if it is unset**).
* Data minimisation: the full date is used in memory and **discarded**; `accounts_agerecord` keeps `birth_year`, `birth_month`, `minimum_age_applied`, `rule_version`, `checked_at`. Never in any serializer; not in the admin. Whether year+month is enough evidence **[COUNSEL]**.
* Under-age: no user / profile / e-mail is stored. The error message is **neutral** ("We can't create an account with these details.") and never mentions the threshold. A same-e-mail **cooldown** (default 24 h, cache-based, keyed by an HMAC of the e-mail, case-insensitive) stops "retry with a different date". Limits: per-process cache unless Redis is configured; a different e-mail bypasses it — self-declaration is inherently bypassable **[COUNSEL: is stronger assurance expected?]**.
* Impossible/future/over-120 dates are rejected with a separate "enter a valid date" message and do not start the cooldown.
* Accounts created before the gate: `POST /api/auth/age/` (same rules, never overwrites). `VEYA_ENFORCE_AGE_GATE=True` (production default) makes accounts without a record **read-only** (writes return 403; reads, the age endpoint and unsubscribing stay available). The mobile app shows a blocking age screen when `profile.age_verified` is false.
* The mobile client validates only that the date is real and not in the future; it does **not** know the minimum.

## Fonts
No custom fonts exist anywhere in the project (no `expo-font`, `fontFamily`, font files or third-party font hosts). The app uses system fonts — nothing added, no licences involved. `tools/audit/scan_repo.py` fails the audit if a third-party font/CDN/analytics/session-recording host appears.

## Security / session log (`securitylog`)
Events: `login_success`, `login_failed`, `logout`, `logout_rejected`, `refresh_failed` (routine refreshes are **not** logged). Stored: event type, user id (null if unknown), **truncated IP** (IPv4 /24, IPv6 /48), **coarse client label** (`android-app`/`ios-app`/`browser`/`script`/`other`), timestamp. **Never stored:** passwords, tokens, the typed e-mail, full IPs, device fingerprints, request bodies. A failed login is linked to the account it targeted (if any) but the attempted address is not stored. Recording failure never breaks login. Events are deleted with the account. Purge: `manage.py purge_security_events` (default **90 days — proposal [COUNSEL]**, `VEYA_SECURITY_LOG_RETENTION_DAYS`), to be scheduled daily. Admin is read-only; the view permission should go only to a named security role. Users can read their own events (`GET /api/security/events/`). Application logs pass through a **redaction filter** (JWTs, bearer tokens, password/secret/token key-values, e-mail addresses). No third-party tracking or screen/session recording exists or was added.

## Marketing e-mail unsubscribe (`mailing`) — mechanism ready, **NOT ACTIVATED**
Nothing in the project sends e-mail and `VEYA_MARKETING_EMAIL_ENABLED` is **False**; no marketing message can leave the system.
* Consent is **opt-in** (default false; optional unticked switch at signup; settings switch) and stores timestamp + source. Whether opt-out is lawful in a market **[COUNSEL]**.
* Unsubscribe link: signed, purpose-bound token (valid 365 days **[COUNSEL]**); `GET` shows a confirmation page and changes nothing (mail scanners prefetch links); `POST` unsubscribes — the page button and the **RFC 8058 one-click** endpoint. No login. Invalid/expired/tampered tokens → 404. The page never shows the address and loads no external resources (CSP `default-src 'none'`).
* Unsubscribing writes a **suppression** entry (HMAC hash of the address, not the address) that survives account deletion; only an explicit authenticated re-opt-in removes it.
* `send_marketing_email` refuses unless: enabled, user active, opted-in, not suppressed; requires `VEYA_PUBLIC_BASE_URL` and a postal address; adds `List-Unsubscribe` + `List-Unsubscribe-Post` headers and a footer. `send_transactional_email` (security / account messages) is a **different category**: not blocked by a marketing unsubscribe, never carries promotions.
* Distinct from account deletion/deactivation (not implemented — see COMPLIANCE_PLAN §4.F).

## Not done / open
Account deletion + data export; privacy policy / terms and acceptance record; DOB policy per country; retention values; processors register; breach procedure; minors safeguards beyond the gate; shared cache (Redis) for cooldown/throttles; scheduling the purge job.
