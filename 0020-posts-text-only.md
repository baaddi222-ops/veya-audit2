# ADR-0020: Text-only posts in 0.2
Date: 2026-10-02 · Status: Accepted · Release: VEYA 0.2

## Decision
`Post` = author + `body` (1–500 chars, non-blank) + `created_at`. No images/video.

## Reason
Media needs an upload pipeline (storage, content-type sniffing, size limits,
moderation hooks). Same reasoning as avatars (ADR-0013): ship the data model and
the authorization boundary first, add media in a later release.

## Consequences
Author is always taken from `request.user` in the view (never the payload);
`PostCreateSerializer` exposes exactly one writable field, `body`.

> **Update (0.4):** posts now accept ONE optional image — see ADR-0024. The body is still required.
