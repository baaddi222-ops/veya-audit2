# VEYA — Security Decisions (Django + React Native stack, 0.5.3)

## The central architectural fact: no RLS backstop

Supabase's RLS meant that even a completely broken or malicious Flutter
client still could not read/write another user's row — the database itself
refused. **Django/DRF has no equivalent by default.** A Django app connects
to Postgres with one shared, privileged role; there is no per-request
Postgres role switching the way Supabase's `anon`/`authenticated` + RLS
policies worked.

**This is not treated as an acceptable gap to quietly live with — it is
treated as the single highest-priority thing to get right in this stack,**
per the master spec's own priority order (security first). The mitigation:

1. **Every "my X" endpoint resolves ownership from `request.user` only.**
   `MyProfileView.get_object()` and `MyPrivacySettingsView.get_object()` do
   not read `self.kwargs` at all — there is no URL parameter for an id to
   even appear in. This is enforced by *absence of a code path*, not a
   runtime check that could be forgotten.
2. **No `/api/profile/<id>/` route exists.** Reading another user's profile
   is not just denied — there is no route that would attempt it. (Same
   decision as ADR-0007: public profile reads are explicitly out of scope
   for this foundation release.)
3. **Serializers are the closed-field boundary.** `ProfileUpdateSerializer`
   lists exactly `username, display_name, avatar_url, bio` — `id`,
   `account_status`, `created_at`, `updated_at` are never in that list, so
   there is no parameter name that would reach them through this
   serializer, regardless of what a client sends in the request body.
4. **`IsActiveAccountOwner` permission** re-implements the Postgres UPDATE
   policy's `account_status = 'active'` condition at the view layer — a
   suspended account cannot modify its own profile even though it's still
   authenticated.
5. **The test suite (`tests/test_profile_ownership.py`) is now the primary
   guard**, not a secondary confirmation of a database-enforced boundary.
   It must stay comprehensive as new endpoints are added — there is no
   database-level fallback if a future view forgets to scope its queryset.

## 0.2 additions

* **One visibility module.** `follows/services.py` decides who can see what
  (own → public account → accepted follower; only ACTIVE accounts). Posts, feed,
  user-posts and public-profile all go through it (ADR-0021).
* **Id-in-URL routes are scoped by queryset, not by an after-the-fact check.**
  `POST follows/requests/<id>/accept/` resolves from follows addressed TO the caller;
  `DELETE posts/<id>/` resolves from the caller's own posts. Someone else's id is a 404.
* **Closed serializers everywhere** — `PostCreateSerializer` = `body` only; all
  cross-user serializers are fully read-only; no `__all__` / `exclude` anywhere
  (checked by `scripts/verify_boundaries.py`).
* **No PII on public surfaces.** Public profile/search/post author objects never
  include email, user id or account_status.
* **Write endpoints** (post, follow, decide) additionally require an ACTIVE account
  (`IsActiveProfile`); a suspended account is read-only.
* **Rate limits** on register/login/refresh/post/follow/search (shared cache needed in prod).

## 0.3 additions

* **Blocks override every other visibility rule** and live in the same single module
  (`follows/services.py`), so posts, feed, comments, search, profile lookup, follow and
  report all inherit them (ADR-0023).
* **Reports cannot probe hidden content** (resolved through the reporter's visible
  querysets) and cannot be forged (closed serializer: type, id, reason, details; reporter /
  status are server-side).
* **Likes/comments/blocks resolve actor from `request.user`; ids in URLs are scoped by queryset**
  (`DELETE comments/<id>/` only sees the caller's comments or comments on the caller's posts).
* New write endpoints are throttled and require an ACTIVE account.
* Admin moderation: report status actions, profile suspend/restore.

## 0.4 additions (full reasoning: ADR-0024)

* **Upload hardening:** bytes are decoded and RE-ENCODED (drops EXIF/GPS + appended payloads); allow-list JPEG/PNG/WEBP;
  5 MB and 40 MP limits; filename/MIME ignored; random storage names; unattached-upload quota; throttle.
* **No public media route.** Images are served only through signed, expiring URLs that appear solely in responses the viewer
  may already see — so private accounts' and blocked users' images are not reachable by browsing or guessing.
* **Attach rules:** uploader-only, kind-matched, single use; others' ids look nonexistent.
* **`avatar_url` write path closed** (arbitrary URLs = tracking/hotlinking); `ProfileUpdateSerializer` is now `username, display_name, bio`.
* **Cleanup:** files die with their post/avatar; cron command for orphans.
* **Residual risk:** a leaked signed URL works for ≤ 12 h (bearer capability). Documented trade-off.

## 0.5 additions (ADR-0025)

* Notification reads/marks are scoped by queryset to the caller's own rows; ids of other users' notifications are 404.
* No notification can be generated about or across a blocked relationship; a block purges existing ones.
* Previews contain only the recipient's own content. No endpoint lists "who has notifications" for anyone else.
* Residual: notifications are polled (no push), so a revoked relationship can leave a stale badge for up to 30 s.

## 0.5.3 additions (ADR-0026)
* **Age gate:** server-authoritative; under-age signup stores nothing; neutral error (no threshold leak); same-e-mail cooldown; only year+month kept; production fails closed without `VEYA_MINIMUM_AGE`; legacy accounts become read-only until they confirm (production default).
* **Security log:** truncated IP + coarse client label only; no credentials/tokens/typed e-mail; recording failures never break login; read-only admin; own events only via API; log redaction filter on all handlers.
* **Unsubscribe:** signed purpose-bound expiring tokens (HMAC-SHA256, constant-time compare); GET never changes state; hashed suppression list; transactional vs marketing separated; marketing not activated.
* **Residual risks:** cooldown/throttle counters are per-process until Redis; self-declared age is bypassable; unsubscribe/age/log retention values are placeholders pending legal review.

## Defects found by reading the 0.1 code (fixed in this release)

Found by static review, since nothing could be executed. Each has a test in
`backend/tests/` (written, not yet run).

| # | Where | Problem | Fix |
|---|---|---|---|
| 1 | `accounts/signals.py` | whole retry loop inside one `atomic()`: after the first IntegrityError the block is broken, so retries would raise TransactionManagementError; retry names also stopped matching the placeholder shape | savepoint per attempt; retry from fresh random hex |
| 2 | `profiles/models.py` | no min-length validator: `ab` passed the serializer, hit the DB CHECK and returned 409 "already in use" (the shipped test expected 400) | `MinLengthValidator(3)`; reserved + placeholder-shaped names rejected |
| 3 | `accounts/migrations/0001` | missing dependency on `auth` (M2M to Group/Permission); spurious `managers=` entry that `makemigrations --check` would flag | corrected |
| 4 | `accounts/admin.py` | stock `UserCreationForm` needs a `username` field; `date_joined` (non-editable) listed as editable → admin add/change pages crash | custom add form, read-only fields |
| 5 | `MyPrivacySettingsView` | suspended account could still change privacy | same permission as profile |
| 6 | accounts | `A@x.com` and `a@x.com` could both register | lowercase on create, case-insensitive lookup/uniqueness |
| 7 | `LogoutView` | would blacklist any refresh token presented | must belong to caller |
| 8 | settings | no throttling, browsable API on, no prod transport hardening | added |
| 9 | models | `CheckConstraint(check=…)` deprecated in Django 5.1 | `condition=` |
| 10 | mobile `AuthContext` | `signUp()` called `signIn()` while holding the in-flight guard → `signIn` returned immediately → never signed in after registering | shared `performSignIn` |
| 11 | mobile `AuthContext` | `atob()` on a base64**url** JWT segment throws for tokens containing `-`/`_` | normalise + pad |
| 12 | mobile | failed refresh didn't reach `AuthContext`; query cache survived sign-out | event + `queryClient.clear()` |

## Authentication

- **JWT via `djangorestframework-simplejwt`**: short-lived access token (15
  min), longer refresh token (30 days) with rotation and blacklisting on
  reuse.
- **Logout blacklists the refresh token** (`LogoutView`) — SimpleJWT does
  not do this automatically; Supabase Auth handled token invalidation for
  us for free in the old stack, so this had to be deliberately implemented
  here, not assumed.
- **Mobile-side token storage**: `expo-secure-store` (Keychain/Keystore) —
  never `AsyncStorage`. Applied from day one this time, rather than found
  as a gap later (as it was in the Flutter phase, ADR-0012).

## Error handling

`core/exceptions.py`'s `veya_exception_handler` maps every exception to
`{"error": {"code", "message"}}` — no Python traceback, no SQLSTATE, no raw
Django/DRF exception class name ever reaches the client. `IntegrityError`
(e.g. duplicate username) becomes a safe 409 message; anything unmapped
becomes a generic 500 with full detail logged server-side only.

## Secrets

`DJANGO_SECRET_KEY`, `DATABASE_URL` — environment variables only
(`django-environ`), never committed, never logged. The mobile app's only
backend-related config value is the API base URL — no backend secret, no
database credential, no JWT signing key ever ships in the mobile bundle.

## Partial verification actually executed (without a Django environment)

Two dependency-free scripts (`backend/scripts/verify_serializer_boundaries.py`,
`verify_placeholder_username.py`) were written and **actually run** in this
environment (plain Python 3.12, no Django needed):

- `verify_serializer_boundaries.py` parses `profiles/serializers.py` with
  Python's `ast` module and confirms, by reading the real source rather
  than eyeballing it, that `ProfileUpdateSerializer`'s writable-field list
  excludes `id`/`account_status`/`created_at`/`updated_at`, and that
  `ProfileSerializer` has zero writable fields. **Result: PASS.**
  (Self-correction worth recording: the first version of this script
  reported a false FAIL on `ProfileSerializer`, because it didn't resolve
  `read_only_fields = fields`-style name references — it treated that
  correct, safe line as if nothing were read-only. Verified against the
  actual source before trusting the result, fixed, re-run. This is
  disclosed because it's a real example of why every automated check here
  is still re-verified against source, not trusted blindly — including
  Claude's own.)
- `verify_placeholder_username.py` re-implements and exercises the
  placeholder-username generation/detection logic identically to
  `accounts/signals.py`/`profiles/models.py`, confirming correct format,
  round-trip detection, and that a real username is never misclassified.
  **Result: PASS.**

**What this does and does not prove:** both scripts genuinely execute real
Python and genuinely test real properties of the real source files. Neither
requires Django, a database, or network access, so both could run here.
Neither is a substitute for `pytest`: they don't exercise HTTP
request/response behavior, the database constraints, cross-user access, or
the permission classes dynamically. The security-critical dynamic test
suite (`tests/test_profile_ownership.py`) remains **WRITTEN, NOT EXECUTED**.

## Verification status — an important asymmetry vs. the Flutter/Supabase phase

In the Supabase-era stack, the *database itself* could be tested for
security directly and independently of the application framework (RLS
policies tested live via `execute_sql`, regardless of whether Flutter code
was even running) — see `supabase/tests/rls_security_tests.sql`'s 15
EXECUTED/VERIFIED scenarios.

**In this stack, the security boundary lives in Django code, which requires
Django itself to run in order to test.** This container has no Django
installed and no network to install it (§1 of the stack-pivot plan). The
ownership-boundary tests in `backend/tests/test_profile_ownership.py` are
therefore currently **WRITTEN, NOT EXECUTED** — a materially different
verification status than the equivalent Flutter-phase tests had. This is
disclosed plainly rather than glossed over: closing this gap (running
`pytest` for real, in an environment with Django installed) is the single
most important remaining step before this stack's 0.1 can be called
verified, not merely implemented.
