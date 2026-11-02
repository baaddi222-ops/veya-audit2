# VEYA — Architecture (Django + React Native stack, 0.2)

## Layers

```
React Native screens/hooks  →  API client (typed)  →  HTTPS/JSON
                                                            │
                                                            ▼
DRF Views (identity from request.user only)  →  Serializers (closed field
list = typed update boundary)  →  Django Models/ORM  →  PostgreSQL
```

Mobile: `src/{auth,profile}/screens` (presentation) → `hooks/` (React Query,
the AsyncNotifier equivalent) → `api.ts` (the only place that calls
`apiClient`) → `client.ts` (the only place that knows the base URL / attaches
the JWT). No screen calls `fetch()` directly — same rule as "no direct
Supabase calls from presentation" (ADR-0005), restated for this stack.

Backend: `views.py` (thin — resolves identity, delegates) → `serializers.py`
(the typed-update boundary) → `models.py` (schema + DB-level constraints).

## Why this shape

- **Django + DRF**: mature, batteries-included, Instagram's own original
  backend choice, strong migration discipline (ADR-0015).
- **PostgreSQL, unchanged**: same engine, carried over from the Supabase
  phase (kept per explicit decision).
- **JWT via SimpleJWT**: standard for a DRF+mobile-client pairing (ADR-0016).
- **Expo**: faster path to an installable build than bare React Native CLI,
  given the same "how do I actually run this on my phone" constraint solved
  via FlutLab for the Flutter phase (ADR-0017).
- **`expo-secure-store`** for token storage, not `AsyncStorage`: the lesson
  from ADR-0012, applied from day one this time (ADR-0018).

## What changed structurally from the Flutter/Supabase phase

**No Row Level Security equivalent.** This is the single biggest
architectural difference and is treated as a first-class risk, not a
footnote — see `docs/SECURITY_DECISIONS.md` and ADR-0019. The authorization
boundary is now entirely in Django view code (`get_object()` always
resolving from `request.user`, never a URL/body-supplied id), with no
database-level backstop. This raises the bar on view-layer test coverage
specifically (`backend/tests/test_profile_ownership.py`).

## 0.2 additions
Backend apps: `accounts`, `profiles` (+ `public_serializers`, `public_views`), `posts`,
`follows` (model + `services.py` = the only place visibility rules live), `core`.
Mobile: `src/posts`, `src/social`, bottom tabs (Feed / Search / Me) + stack screens
(CreatePost, UserProfile, Requests, EditProfile). Every list uses cursor pagination
(`src/api/pagination.ts`); query keys are scoped by user id and the cache is cleared
on sign-out / session expiry. Full route list: `docs/API.md`.

## 0.3 additions
Backend apps `safety` (Block, Report, admin review) and `engagement` (PostLike, Comment,
`annotate_engagement`). Block-aware visibility is centralised in `follows/services.py`.
Mobile: `src/posts` (likes, comments), `src/social` (block, report, blocked list).

## 0.4 additions
Backend app `media` (Image, `processing.py` validate+re-encode, `signing.py`, serve view, cleanup command, signals).
`posts.Post.image` and `profiles.Profile.avatar` point at it. Mobile: `src/media` (picker, upload), `Avatar`, image in `PostCard`.

## 0.5 additions
Backend app `notifications` (model, `notify()` service called from follow/like/comment views, list/unread/read endpoints).
Mobile: `src/notifications` + "Alerts" tab with an unread badge.

## What 0.5 does NOT contain
Push, realtime, video, messaging, discovery feed, payments. (0.6+.)
