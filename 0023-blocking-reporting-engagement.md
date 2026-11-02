# ADR-0023: Mutual-invisibility blocks, scoped reports, likes & comments
Date: 2026-10-04 · Status: Accepted · Release: VEYA 0.3

## Blocks
A block in EITHER direction makes the two accounts invisible to each other: profile
(404), posts, comments, search, feed; follows in both directions are deleted at block
time and a new follow is refused (404). Enforced in ONE place (`follows/services.py`:
`can_view_content`, `visible_posts`, `feed_posts`, `visible_comments`, `exclude_blocked`).
Who blocked ME is never exposed (`GET safety/blocks/` lists only blocks I made). A blocked
user cannot undo someone else's block (the DELETE only touches rows where the caller is the blocker).

## Reports
`POST safety/reports/ {target_type user|post|comment, target_id, reason, details}`.
You can only report what you can SEE (resolved through the visibility querysets), so the
endpoint cannot probe hidden content — invisible = 404. No self-reports. Idempotent
(unique reporter+target). `target_id` is not a FK so reports survive deleted content.
Review happens in Django admin (status actions) — the Control Center comes later.
Profiles can be suspended/restored from admin.

## Likes & comments
Like/unlike is idempotent and only possible on posts in the viewer's visible set.
Counts are exposed, the list of likers is not. Comments: 1–300 chars, listed newest-first
with blocked/inactive authors hidden; deletable by the comment author OR the post author;
anyone else's id is a 404. Comment-likes are NOT in 0.3.

## Known trade-offs
* `like_count`/`comment_count` are raw totals: they include comments from users the viewer
  has blocked (the comments themselves are hidden).
* Admin-only moderation: no in-app moderator role yet.
