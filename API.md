# VEYA API (0.5.3)
All routes under `/api/`, JSON, `Authorization: Bearer <access>` unless noted.
Errors: `{"error": {"code", "message", "fields"?}}`. Lists: `{"next", "previous", "results"}` (cursor).

| Method & path | Purpose | Notes |
|---|---|---|
| POST `auth/register/` | sign up `{email, password, date_of_birth (YYYY-MM-DD), marketing_opt_in? (default false)}` | no auth; throttled 10/h; under-age → 400 with a neutral message and **nothing stored**; only birth year+month are kept |
| POST `auth/token/` · `auth/token/refresh/` | login / refresh | no auth; throttled |
| POST `auth/logout/` | blacklist own refresh token | body `{refresh}` |
| GET/PATCH `profile/me/` | my profile | writable: username, display_name, avatar_url, bio |
| GET/PATCH `profile/me/privacy/` | my privacy | `is_private_account` |
| GET `users/search/?q=` | username-prefix search (q ≥ 2 chars) | |
| GET `users/<username>/` | public profile + `relationship` | bio/post_count hidden if not visible |
| GET `users/<username>/posts/` | that user's posts | 403 if private & not followed |
| POST/DELETE `users/<username>/follow/` | follow (or request) / unfollow / cancel | |
| GET `follows/requests/` | my incoming pending requests | |
| POST `follows/requests/<id>/accept\|decline/` | decide a request addressed to me | others' ids → 404 |
| POST `posts/` | create `{body, image_id?}` (1–500) | active accounts only; 60/h; `image_id` must be your own unused `post` image |
| GET/DELETE `posts/<id>/` | read (if visible) / delete (author only) | |
| GET `feed/` | own + followed accounts' posts | each post has `like_count`, `comment_count`, `liked_by_me` |
| POST/DELETE `posts/<id>/like/` | like / unlike (idempotent) | only visible posts; 300/h |
| GET/POST `posts/<id>/comments/` | list / add `{body}` (1–300) | blocked authors hidden; 120/h |
| DELETE `comments/<id>/` | comment author or post author | others' ids → 404 |
| POST/DELETE `users/<username>/block/` | block / unblock | mutual invisibility; removes follows |
| GET `safety/blocks/` | users I blocked | |
| POST `safety/reports/` | `{target_type, target_id, reason, details?}` | only what you can see; 20/h |
| POST `media/` | upload (multipart `kind=post\|avatar`, `file`) → `{id,width,height}` | JPEG/PNG/WEBP ≤ 5 MB; re-encoded; 30/h |
| GET `media/<id>/<full\|thumb>/?s=<sig>` | image bytes | no auth header; signature from API responses (6–12 h) |
| PUT/DELETE `profile/me/avatar/` | set `{image_id}` / remove avatar | your own unused `avatar` image |

Post objects now include `image: {url, thumb_url, width, height} | null`; every profile summary / profile has a signed `avatar_url` (or null).
`PATCH profile/me/` no longer accepts `avatar_url`.
| GET `notifications/` | my notifications (newest first, cursor) | `{id,type,actor,post_id,post_preview,comment_text,created_at,read}` |
| GET `notifications/unread-count/` | `{count}` | polled by the app |
| POST `notifications/<id>/read/` · `notifications/read-all/` | mark read | only my own rows; others' ids → 404 |
| POST `auth/age/` | `{date_of_birth}` for accounts without an age check | same rules/cooldown as signup; never overwrites; 10/h |
| GET `security/events/` | my own security events (login/logout/failures) | `{id,event_type,ip_prefix,user_agent_family,created_at}` |
| GET/PATCH `mailing/preferences/` | my marketing e-mail preference `{marketing_opt_in}` | opt-in only; works for suspended users |
| GET/POST `mailing/unsubscribe/<token>/` | public unsubscribe page (GET: no state change) / unsubscribe (POST, also RFC 8058 one-click) | no auth; signed token; 404 if invalid/expired; 60/h |

`GET profile/me/` now includes `age_verified` (never the birth date). With `VEYA_ENFORCE_AGE_GATE=True`, write endpoints return 403 for accounts without an age check.
