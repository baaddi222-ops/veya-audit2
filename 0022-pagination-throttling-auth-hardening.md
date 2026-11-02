# ADR-0022: Cursor pagination, scoped throttles, auth hardening
Date: 2026-10-02 · Status: Accepted · Release: VEYA 0.2

* All list endpoints use DRF `CursorPagination` (stable under inserts; no deep-offset cost).
* `ScopedRateThrottle` on register/login/refresh/post-create/follow/search. Counters
  use Django's cache: the default LocMemCache is per-process, so production MUST
  configure a shared cache (Redis) or limits are per-worker.
* Emails are stored lowercased and looked up case-insensitively (a unique index alone is
  case-sensitive).
* Logout only blacklists a refresh token belonging to the caller.
* JSON renderer only (no browsable API).
