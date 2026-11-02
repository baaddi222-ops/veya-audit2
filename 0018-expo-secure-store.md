# ADR-0018: expo-secure-store for token persistence

Date: 2026-09-30
Status: Accepted
Release: VEYA 0.1 (stack pivot)

## Decision
JWT access/refresh tokens are persisted via `expo-secure-store` (Keychain
on iOS, Keystore-backed encrypted storage on Android) — never
`AsyncStorage`.

## Context / Problem
The Flutter phase shipped with unencrypted `SharedPreferences` token
storage by the Supabase SDK's own default, found as a real gap in the 0.1-D
audit and fixed afterward (ADR-0012). This stack starts fresh — the
question is whether to repeat that mistake or avoid it from day one.

## Alternatives Considered
- `AsyncStorage` (React Native's plain default): unencrypted, the direct RN
  analogue of the SharedPreferences gap already found once.
- `react-native-keychain`: also viable, but requires native linking that
  complicates Expo's managed workflow (ADR-0017); `expo-secure-store` is
  the Expo-native equivalent with no such friction.

## Reason for Decision
Given the Flutter phase already demonstrated this exact mistake and its
cost (a follow-up fix, a new dependency, a new ADR, after the fact),
applying the lesson from the start avoids repeating it.

## Consequences
None significant — `expo-secure-store` is a drop-in, Expo-maintained
package with no native-linking overhead in the managed workflow.
