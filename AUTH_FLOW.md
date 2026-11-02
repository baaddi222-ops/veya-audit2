# VEYA — Auth Flow (Django + React Native stack, 0.1)

## Sign up
1. `SignUpScreen` → `AuthContext.signUp()` sets state to `authenticating`.
2. `POST /api/auth/register/` (email + password only — `RegisterSerializer`'s
   closed field list) creates the `User`; `create_profile_for_new_user`
   fires in the same transaction, creating `Profile` (placeholder username)
   + `PrivacySettings`.
3. Registration issues no token by design — `signUp()` immediately runs the
   same sign-in request (`performSignIn`, sharing the in-flight guard), mirroring how the Flutter phase's `AuthNotifier`
   handled "no session returned" as a real case to resolve, not a silent
   dead end.
4. `RootNavigator` reads `state.kind`; once `authenticated`, it loads the
   profile and — since `hasPlaceholderUsername` is true right after signup —
   shows `CompleteProfileScreen`.

## Sign in
`POST /api/auth/token/` (SimpleJWT's `TokenObtainPairView`) returns
`{access, refresh}`; both are written to `expo-secure-store` before state
becomes `authenticated`.

## Sign out
`AuthContext.signOut()` sets `signingOut` immediately (the fail-closed rule
in `RootNavigator` means protected screens stop being reachable at this
instant, not once the network call completes) → `POST /api/auth/logout/`
blacklists the refresh token (best-effort; failure never blocks local
sign-out, same "force local unauthenticated regardless" rule as the Flutter
phase) → tokens cleared from secure storage → `unauthenticated`.

## Session restoration
On app start, `AuthProvider`'s effect reads whatever is in
`expo-secure-store` and resolves directly to `authenticated` or
`unauthenticated` — no network round-trip required to know which screen to
show first (the access token's presence is enough for routing; the first
authenticated API call will fail cleanly with 401 if the token has actually
expired, handled the same way any other API error is — see below).

## Token expiration
`apiClient.request()` transparently handles access-token expiry: a 401
triggers exactly one `POST /api/auth/token/refresh/` call (de-duplicated —
several simultaneous 401s share one refresh attempt, not one each) and one
retry of the original request. A failed refresh clears stored tokens and
lets the 401 surface as a normal `ApiError`, which `ProfileScreen`'s error
state already handles (retry / sign out).

**Session expiry (fixed in 0.2):** when a refresh fails, `apiClient` emits a
session-expired event; `AuthProvider` subscribes, clears the React Query cache and
moves to `unauthenticated` immediately.

## Verification status
Implemented and statically reviewed (all Python files pass real syntax
validation via `ast.parse` — see RELEASE_STATUS.md). **Not executed**: no
Django installed (no network) to run the backend, no `npm install` to run
the mobile app or its tests. The live-tested part is the database schema
itself (see DATABASE_SCHEMA.md) — the request/response flow above has not
been exercised end-to-end.
