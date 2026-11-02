# VEYA Compliance Plan — PLANNING DOCUMENT (nothing in it is implemented)
Version 2 · 2026-10-30 · **Status: the four owner rules are now IMPLEMENTED IN CODE in release 0.5.3 (ADR-0026), but none of the Django-layer code has been executed (no Django here). Legal parameters are undecided. 0.6 has not started.**

## Implementation status (what the code really does today)
| Rule | Code state | Evidence | Still undecided / not done |
|---|---|---|---|
| 1. Age at signup | **WRITTEN — NOT EXECUTED** (API, DB, mobile screens). Age arithmetic: **EXECUTED — PASS** (6 tests). Mobile date parsing: **EXECUTED — PASS** (8 tests, shim) | `accounts/age.py`, `AgeRecord`, `RegisterSerializer`, `POST /auth/age/`, `SignUpScreen`, `AgeGateScreen`; 20 pytest functions written | **the minimum age** (dev placeholder 16, production refuses to start without it) **[COUNSEL]**; cooldown length; is year+month evidence enough; stronger age assurance |
| 2. Fonts local | **STATICALLY VERIFIED**: system fonts only; no custom font, `expo-font`, `fontFamily`, font file or third-party font host anywhere; **nothing added** (no licences involved). Enforced by `scan_repo.py` | grep + scan + selftest case | register of external connections must stay current |
| 3. Session / security logs | helpers + redaction **EXECUTED — PASS** (15 tests); DB/API/admin **WRITTEN — NOT EXECUTED** (13 pytest functions) | `securitylog` app, redaction filter on all log handlers | retention (90 days = proposal) **[COUNSEL]**; scheduling the purge job; who gets the admin view permission |
| 4. Marketing unsubscribe | tokens + policy **EXECUTED — PASS** (12 tests); endpoints/senders **WRITTEN — NOT EXECUTED** (19 pytest functions). **NOT ACTIVATED**: no e-mail is sent, `VEYA_MARKETING_EMAIL_ENABLED=False` | `mailing` app | opt-in vs opt-out per market, token lifetime, sender postal address, e-mail provider **[COUNSEL]** |
| Account deletion / export, privacy policy + terms + acceptance record, minors safeguards beyond the gate | **NOT DONE** | — | §4.E–G |



> **Not legal advice.** Following this plan does **not** guarantee that fines, claims or app-store rejections will be avoided. Every item tagged
> **[COUNSEL]** depends on the countries you target, your company's location and your processors, and must be confirmed by qualified counsel in
> those jurisdictions. Legal facts quoted below are from general knowledge and tagged *(verify)* where they change often or vary by country.
> Technical sections describe what engineering can do; they do not decide what the law requires.

## 0. How this plan relates to the rest of the project
* The audit (`docs/AUDIT_0.5.md`, accepted baseline 0.5.2) is **still open**: `run_all.sh` must exit 0 on a connected machine first (`docs/RUN_BLOCKED_CHECKS.md`, "QUICK PATH").
* Order of work: **(1)** close the audit blockers → **(2)** you approve this plan and answer §1 → **(3)** compliance releases C1…C6 (§8) → **(4)** only then 0.6.
* Your four rules (`COMPLIANCE_REQUIREMENTS.md`) map to: age check → §4.A · local fonts → §4.B · session logs → §4.C · unsubscribe link → §4.D.

## 1. Decisions I need from you (nothing below can be finalised without them)
1. **Target countries/markets** for launch and the next 12 months (e.g. Morocco, France/EU, Gulf, US, UK). *Everything in §3 depends on this.*
2. **Who is the "data controller"**: your company/legal entity, its country, and whether you have an establishment in the EU (otherwise an EU representative may be needed) **[COUNSEL]**.
3. **Do you intend to allow users under 18?** (13–17) — and if yes, from which minimum age.
4. **Hosting region/provider** for the database and media (affects cross-border transfer rules) and the **e-mail provider** you will use.
5. **Will VEYA send any e-mail soon?** (verification, password reset, notifications, marketing). Today it sends none.
6. **Session logging**: confirm it means an **authentication/security log** (login, logout, failed attempts, session revocation), **not** third-party session *recording* (Hotjar/FullStory-style screen capture, which this plan does not include and the repo scan blocks).
7. **Who handles privacy requests and abuse reports** (a named person/mailbox) and the response times you can commit to.
8. **Payments/promotions timeline** (they add processors, tax and consumer-law duties — out of scope here, flagged in §7).

## 2. What VEYA collects today (data inventory, from the code)
| Area | Data | Where | Notes |
|---|---|---|---|
| Account | e-mail, password **hash**, `is_active`, `is_staff`, `date_joined`, `last_login` | `accounts_user` | e-mail stored lowercased |
| Profile | username, display name, bio, avatar (image), `account_status`, timestamps; `is_private_account` (default **true**) | `profiles_*` | private-by-default is already a minors-friendly default |
| Content | post text (≤500), optional post image (re-encoded JPEG, **EXIF/GPS stripped**), comments (≤300), likes | `posts_*`, `engagement_*`, `media_image` | files on server storage; served only via signed expiring URLs |
| Social graph | follows/requests, blocks | `follows_*`, `safety_block` | |
| Safety | reports (reporter, target, reason, free text) | `safety_report` | reviewed in Django admin |
| Notifications | in-app notification rows | `notifications_*` | no push yet |
| Auth tokens | JWT blacklist/outstanding-token tables (token id, user, created/expiry) | `token_blacklist_*` | not a user-facing log |
| Operational | application error logs; web-server access logs (IP) at the hosting layer; throttle counters keyed by user/IP in cache | outside the DB | **to be controlled** (§4.C) |
| **Not collected today** | date of birth/age, phone, real name, location, device IDs, advertising IDs, analytics, push tokens, stored IP history, e-mail sending history | — | each future addition needs this table updated first |

## 3. Market matrix (assumptions to be confirmed — **[COUNSEL]** for every row)
| Market | Main data-protection rules (name only) | Age / minors point to confirm | Other points to confirm |
|---|---|---|---|
| **Morocco** (likely primary market) | Law 09-08 on personal-data protection; regulator **CNDP** | I cannot state a specific social-media minimum age for Morocco with confidence; civil majority is 18 — confirm whether parental consent is required for minors | prior declaration/authorisation to CNDP for processing; **authorisation for transfers abroad** (e.g. foreign cloud hosting); local-language notices; consumer-law rules for paid features |
| **EU / EEA** (if targeted, even from outside) | GDPR (+ ePrivacy for cookies/e-mail marketing) | GDPR Art. 8: digital-consent age is 16 by default, member states may set 13–16 (e.g. France 15, Spain 14, Italy 14, Germany 16) *(verify each)* | EU representative if no EU establishment; DPIA for children's data; DSA obligations depending on size/role; records of processing; breach notification (72h) |
| **United Kingdom** | UK GDPR + Data Protection Act 2018 | consent age 13; ICO **Children's Code**; Online Safety Act duties *(verify)* | UK representative |
| **United States** | COPPA (under 13: verifiable parental consent; "actual knowledge" triggers), state privacy and minors/social-media laws that vary by state *(verify)*; CAN-SPAM | under 13 not allowed without COPPA program — simplest is to **block under 13** | mandatory reporting of apparent CSAM by providers (18 U.S.C. §2258A) — process needed |
| **Gulf (UAE / KSA …)** | national PDPLs (UAE PDPL, KSA PDPL) *(verify)* | minors rules differ per country | data-localisation/transfer rules; content-regulation rules |
**Recommendation until counsel decides:** apply the **strictest minimum age among your chosen markets** globally (a single threshold is far simpler and safer to build than per-country logic), and treat 13–15 as "not allowed at launch" unless counsel advises a consent flow.

## 4. Workstreams

### 4.A Age assurance and minimum age (your rule 1)
**Goal:** do not onboard people below the minimum age you choose, and record that a check was made — with the least data possible.
* **Policy options** (decision in §1.3): **(1)** one global minimum (e.g. 16) — simplest; **(2)** per-country thresholds (needs country at signup + counsel's table); **(3)** 13+ with parental-consent flows where required (heaviest). Default proposal: option 1.
* **Mechanism (self-declaration, neutral):** the signup screen asks for **date of birth** *before* showing any minimum-age hint ("age fishing" avoidance); under-age ⇒ rejected with a neutral message; **no account, no e-mail stored**; a short cooldown on the same device/e-mail-hash to stop retry-until-pass. Self-declaration is easy to bypass — whether stronger age assurance (ID/face estimation) is expected in your markets is a **[COUNSEL]** question; it carries its own privacy risk and cost.
* **Data model (proposal):** separate table `accounts_agerecord(user, date_of_birth, checked_at, rule_version, minimum_applied)`; never in any public serializer; not editable after signup except via a reviewed support process. Minimisation alternative: store only `birth_year_month` or an `is_over_minimum` flag + `checked_at` (cannot later tell when a minor becomes an adult) — pick with counsel.
* **Existing accounts (created without DOB):** on next login they must complete the age step before any write action; until then treated as "unverified" (read-only) — decision needed.
* **Findings after signup:** a report category "under-age account", an admin action to suspend and a deletion procedure; if the law ties duties to "actual knowledge", the process must be documented **[COUNSEL]**.
* **API/UI changes (when approved):** `POST /api/auth/register/` gains `date_of_birth`, `accepted_terms_version`; new signup screens; tests: under-age rejected, exact birthday boundary, future/absurd dates, leap-day, no DOB in any API response, existing-account gate.

### 4.B Local fonts and external connections (your rule 2)
* **Today:** the mobile app uses system fonts; **no third-party font, CDN, analytics or session-recording host exists in the source**, and `tools/audit/scan_repo.py` fails the audit if one appears (proven by the failure-injection self-test).
* **If custom fonts are wanted:** ship the font files inside the app (`mobile/assets/fonts`, loaded with `expo-font`) or serve them from **your own domain**; never from Google Fonts/Typekit/CDNs (a 2022 German court decision treated embedding Google Fonts from Google's servers as a privacy violation *(verify)*). For any website (privacy-policy page, landing page, admin) add a `Content-Security-Policy` with `font-src 'self'` and self-host assets.
* **External connections register (keep it current — every row needs a purpose, a legal basis and a processor agreement where personal data is sent):**

| Connection | Needed? | Data sent | Status |
|---|---|---|---|
| App → VEYA API (`EXPO_PUBLIC_API_BASE_URL`) | yes | all API traffic | the only runtime connection in app source today |
| Images/media | yes | served by VEYA API (signed URLs) | self-hosted; move to object storage/CDN later → add a row |
| Expo Go / Metro dev server | development only | dev traffic | not present in production builds |
| App Store / Google Play services | yes (distribution, store-side crash/analytics are the stores', not yours) | store-defined | declare in privacy labels |
| Push (APNs/FCM) | later | device tokens | **new processor** when added |
| E-mail provider | later | e-mail address, message | **new processor** when added |
| Error tracking (e.g. Sentry) / analytics | optional | IP, device, stack traces | **not present**; adding requires scrubbing, consent assessment **[COUNSEL]** |
| Payments / hosting / object storage | later / yes | per provider | add rows + data-processing agreements + transfer assessment |
* **Enforcement:** keep `scan_repo.py` mandatory in `run_all.sh`; add a CI step that fails on new hosts; add a "connections" section to the privacy policy generated from this table.

### 4.C Login-session logs and security events (your rule 3)
**Purpose limitation:** security (detect account takeover/abuse), support for the account owner, legal obligations. **Not** behavioural analytics.
* **Events (proposal):** login success/failure, logout, refresh-token reuse/failure, password change/reset, e-mail change, session revoked, account status change, admin actions (Django already keeps `LogEntry`), report-handling actions. **Do not log** passwords, tokens, full e-mail on failed logins, request bodies, or content.
* **Fields:** user id (or null), event type, outcome/reason code, timestamp, **truncated IP** (IPv4 /24, IPv6 /48) or keyed hash, coarse user-agent (OS/app version), session id (token jti) — no device fingerprinting, no precise location.
* **Retention (proposal, to confirm [COUNSEL]):** routine auth events **90 days**; events flagged as security incidents up to **12 months**; automatic purge job (scheduled, logged); deleted with the account except what must be kept for a documented legal/security reason.
* **Access control:** separate table; readable only by a named **security** role (not by general support/moderators); every read in admin is itself audited; encryption at rest at the hosting layer; no log lines with PII in stdout/app logs (add a logging filter + test).
* **User-facing:** "Active sessions" screen (device label, last used, coarse location from truncated IP not shown) and **revoke** (blacklists the refresh token) — also helps the user.
* **Legal basis/notice:** typically legitimate interest (security) *(verify)*; must be disclosed in the privacy policy with retention periods **[COUNSEL]**. These logs are included in access/export requests (§4.F).
* **Third-party session recording** (Hotjar etc.): **not planned**; if ever wanted it needs a separate assessment, input masking and consent.

### 4.D E-mail: unsubscribe vs notification settings vs account deactivation vs deletion (your rule 4)
Four different things; the product and the policy must keep them separate:

| Action | What it does | Where | Needs login? | Effect on data |
|---|---|---|---|---|
| **Unsubscribe from marketing e-mail** | stops *marketing* messages only | link in every marketing e-mail + `List-Unsubscribe` headers; also a toggle in settings | **no** (one click) | store the preference + a **suppression entry** (hashed e-mail) so it is honoured even if data is later deleted |
| **Notification preferences** | choose in-app/push/e-mail notifications by category | settings screen | yes | preference rows |
| **Deactivate (pause) account** | hide profile/content, keep data, reversible | settings | yes (re-auth) | no deletion |
| **Delete account / erase data** | permanent erasure after a grace period (§4.F) | in-app **and** web link (required by the stores, §4.H) | yes (re-auth) | content, profile, relations erased; limited records retained for legal/safety reasons **[COUNSEL]** |
"Stop the service" for a user = deactivate or delete; for a *processing* objection or consent withdrawal see §4.F.
* **Rules for marketing e-mail** *(verify per market)*: prior consent where opt-in is required (EU/ePrivacy), clear sender identity, physical address (CAN-SPAM), unsubscribe honoured promptly (the major mailbox providers expect one-click unsubscribe with `List-Unsubscribe` + `List-Unsubscribe-Post` (RFC 8058) for bulk senders; CAN-SPAM allows up to 10 business days but sooner is the target), no dark patterns, consent record (timestamp, source, text version).
* **Transactional/security e-mail** (verification, password reset, security alerts, legal notices) is **not** marketing and is not suppressed by unsubscribing — but it must stay minimal and must not contain promotions.
* **Technical design (when e-mail exists):** signed, non-guessable unsubscribe tokens; idempotent endpoint; per-category preferences; suppression list; bounce/complaint handling; tests that unsubscribing one user cannot affect another and that tokens expire/are single-purpose.

### 4.E Privacy Policy and Terms of Use / EULA
* **Privacy Policy (contents):** controller identity + contact (+ DPO/representative if applicable); the §2 inventory in plain language; purposes and **legal bases**; recipients/processors (from the §4.B register); international transfers and safeguards; **retention table** (§4.C and per data type); user rights and how to use them (§4.F); children (§4.G); security measures at a high level; cookies/local storage (the API uses tokens, no cookies; Django admin uses a session cookie); change notification; effective date + version; local-language versions **[COUNSEL]**.
* **Terms of Use / EULA (contents):** eligibility and minimum age; account rules; **user-generated-content rules** (prohibited content, reporting, moderation, suspension/termination, appeal); licence the user grants for their content and the user's responsibility; copyright-takedown procedure; third-party/app-store terms; liability, governing law, dispute resolution **[COUNSEL]**; paid-feature terms later.
* **Engineering support:** `terms_version` + `privacy_version` constants; store `accepted_terms_version`, `accepted_at` at signup; re-acceptance flow when versions change materially; policy URLs reachable without login (the stores require them); the mobile app links to both.
* **Process:** draft by owner/counsel → counsel review per market → publish → version; engineering never edits legal text.

### 4.F Data-subject requests: access, correction, deletion, portability, objection
* **Correction:** already possible for username/display name/bio (`PATCH /api/profile/me/`); e-mail change flow to be added with re-verification.
* **Access / portability:** `POST /api/privacy/export/` (re-authentication required, rate-limited) creates an **asynchronous job** producing a machine-readable **JSON** (+ media files) of: account, profile, posts, comments, likes, follows, blocks, reports **made by** the user, notifications, auth events (§4.C), consents/age record; delivered via a short-lived signed link, then purged. Excludes other people's private data (e.g. content of others' comments on your posts beyond what is already yours to see).
* **Deletion/erasure:** `DELETE /api/account/` (re-authentication) → account is deactivated immediately → **grace period (proposal 14–30 days, user can cancel)** → purge job deletes user, profile, posts, comments, likes, follows, notifications, images **and files** (the existing signals already delete files with rows); **reports about the user and suspected-abuse records** may be retained in minimal form for a defined period **[COUNSEL]**; **backups** expire on a documented schedule (state it in the policy).
* **Restriction/objection/consent withdrawal:** handled through settings where possible (private account, notification/marketing preferences) and otherwise through the privacy mailbox with a ticket id.
* **Operations:** identity check = logged-in session + re-auth (or e-mail proof for logged-out requests); response deadlines per market (GDPR: one month, extendable *(verify)*); a request log (type, date, outcome) kept as evidence; admin tooling for manual cases; tests that exports contain **only** the requester's data and that deletion leaves no orphan rows/files.

### 4.G Protection of minors (where applicable)
Applies if §1.3 allows under-18 users, and in every case to the **under-age handling** in §4.A.
* **Safer defaults (some already exist):** accounts private by default ✅; restrict discoverability of minors in search and suggestions; no contact from unknown adults once messaging exists (messaging must be designed with age rules *before* it is built); no promotions/targeted advertising to minors; reports + blocks ✅.
* **Data minimisation for minors:** no precise location (EXIF already stripped ✅), no behavioural profiling, shorter retention, no marketing e-mail.
* **Parental involvement** where required by law/policy **[COUNSEL]**.
* **Moderation & escalation:** report reasons already include self-harm and sexual content ✅; define response times, an escalation path, evidence preservation, law-enforcement request handling, and a **CSAM response procedure** (removal, preservation, reporting to the competent authority/NCMEC where applicable) **[COUNSEL]**; consider hash-matching vendors.
* **Assessments:** a **DPIA** (or local equivalent) before launching to minors **[COUNSEL]**; follow the UK Children's Code / local equivalents where the market applies.
* **Store age ratings:** answer the Apple/Google questionnaires consistently with the above (UGC without strong moderation raises the rating).

### 4.H App-store requirements that behave like compliance requirements
*(verify current text before submission)* — **in-app account deletion** is required by Apple (guideline 5.1.1(v)) and Google Play (plus a web deletion link); user-generated-content apps need **report, block, moderation, contact details and terms** (Apple 1.2; Google UGC policy) — report/block exist ✅, terms and deletion do not yet; privacy labels/Data Safety forms must match §2/§4.B; privacy-policy URL mandatory. **These make C1–C3 prerequisites for any store submission**, independent of any fine risk.

## 5. Current state vs. requirement
| Requirement | State | Gap |
|---|---|---|
| Age check at signup | ✅ written (not executed); policy value undecided | §4.A |
| Local fonts / no third-party hosts | ✅ enforced by audit scan | document register; keep scan |
| Auth/security event log | ✅ written (not executed); session management screen not built | §4.C |
| Unsubscribe | ✅ mechanism written, not activated (no e-mail is sent) | §4.D |
| Privacy Policy / Terms / acceptance record | ❌ | §4.E |
| Export / correction / deletion | correction ✅ partial; export ❌; deletion ❌ | §4.F (also store-required) |
| Minors protections | partial (private default, block, report, EXIF stripped) | §4.G |
| Report/block/moderation (UGC) | ✅ basic (admin review) | SLAs, appeals, procedures |
| Image privacy | ✅ EXIF/GPS stripped, signed URLs | — |

## 6. Counsel-review register (give this list to your lawyer)
1. Applicable laws per market (§3) and the **strictest minimum age**; parental-consent requirements. 2. Controller identity, EU/UK representative, CNDP declaration/authorisation and **cross-border transfer authorisation** for your hosting. 3. Legal bases per purpose (account, security logs, notifications, marketing). 4. Retention periods (§4.C, §4.F) and what may be kept after deletion. 5. Privacy Policy and Terms/EULA text (local languages). 6. E-mail marketing consent model per market. 7. DPIA for minors. 8. CSAM/abuse reporting duties and law-enforcement request handling. 9. Breach-notification procedure and contacts. 10. Cookie/ePrivacy needs for any web property. 11. Consumer-law rules for paid features (later). 12. Whether stronger age assurance is expected.

## 7. Out of scope here but will need their own plans
Payments, promotions, subscriptions, tax and consumer-protection rules; messaging (end-to-end privacy, age-based contact limits); video; push notifications; analytics; AI operators handling user data.

## 8. Proposed release sequence (after the audit passes and you approve this plan)
| Release | Content | Acceptance (all with executed tests) |
|---|---|---|
| **C0** | answers to §1; counsel engaged; policy drafts started | decisions recorded |
| **C1** | policy/terms versioning + acceptance at signup + public policy URLs | acceptance stored; versions enforced; screens link to documents |
| **C2** | age gate (§4.A) + existing-account gate | boundary tests; no DOB leak; under-age leaves no data |
| **C3** | account deletion + data export (§4.F) | export contains only own data; deletion leaves no rows/files; grace-period cancel works |
| **C4** | auth/security event log + active sessions + retention job + access control (§4.C) | no PII in app logs; purge tested; revoke works |
| **C5** | e-mail infrastructure + unsubscribe + preferences (§4.D) — only when the first e-mail is introduced | one-click unsubscribe; no cross-user effect; suppression list honoured |
| **C6** | minors safeguards + moderation procedures + DPIA inputs (§4.G) | defaults enforced for minors; escalation tested |
Each release: new tests written first, `run_all.sh` exit 0 on a connected machine, no regression of 0.1–0.5, backup before changes.

## 9. Risks
Self-declared age is bypassable · retention/erasure vs. safety evidence trade-offs · cross-border hosting authorisations may delay launch · e-mail/push/payment providers add processors and notices · policy text drifting from reality (keep §2/§4.B tables as the source of truth) · this plan is only as good as the answers to §1 and the counsel review.
