# ADR-0017: Expo over bare React Native CLI

Date: 2026-09-30
Status: Accepted
Release: VEYA 0.1 (stack pivot)

## Decision
Use Expo (managed workflow) rather than the bare React Native CLI.

## Context / Problem
The project owner's development environment is phone-only, with no local
computer for native Android/iOS build tooling (the same constraint that
made FlutLab necessary for the Flutter phase). React Native's bare CLI
requires Xcode/Android Studio locally for anything beyond JS bundling.

## Alternatives Considered
- Bare React Native CLI: full native control, but requires native build
  tooling that isn't available in a phone-only setup at all — a much
  harder blocker than Flutter's was (FlutLab could still invoke
  `flutter build` remotely; bare RN's native modules often need local
  Xcode/Android Studio for anything beyond a pure-JS change).
- Expo with EAS Build: cloud-hosted build service, directly analogous to
  how FlutLab solved "how do I get an installable app with no computer."

## Reason for Decision
Expo's managed workflow plus EAS Build directly reproduces the
FlutLab-solved workflow for this stack: write code, request a cloud build,
download an installable app — achievable from a phone browser.

## Consequences
Some native modules require Expo-compatible packages (or a one-time "prebuild"
step) rather than arbitrary bare-RN native modules — `expo-secure-store`
was chosen specifically because it fits this constraint (ADR-0018).
