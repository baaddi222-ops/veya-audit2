# VEYA — Database Schema (Django stack, 0.5.3)

Fifteen tables (Django adds its own `django_migrations`, `django_content_type`,
`auth_permission`, etc. automatically — not listed here, not application data).

## `accounts_user` (Django's `AUTH_USER_MODEL`)

| Column | Type | Notes |
|---|---|---|
| `id` | uuid, PK | Custom user model — set from day one to avoid Django's well-known "change AUTH_USER_MODEL after the fact" migration trap |
| `email` | varchar(254), unique | Login field (`USERNAME_FIELD`) |
| `password` | varchar(128) | Django's own PBKDF2/Argon2 hashing, not custom |
| `is_active`, `is_staff`, `is_superuser` | bool | Django auth framework fields |
| `date_joined` | timestamptz | |

## `profiles_profile`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid, PK | |
| `user_id` | uuid, unique FK → accounts_user, cascade delete | 1:1 |
| `username` | varchar(24), unique | CHECK constraint `^[a-z0-9_]{3,24}$` — same rule as the Flutter-phase schema |
| `display_name` | varchar(50), null | length enforced at BOTH the varchar(50) column-type level AND an explicit CHECK (found live: varchar(N) alone already rejects longer values with `22001`, before the CHECK's `23514` would even fire — genuine defense-in-depth, confirmed during 0.1 schema validation) |
| `avatar_url` | varchar(200), null | DEPRECATED in 0.4 — no longer client-writable |
| `avatar_id` | uuid FK → media_image, null, SET NULL | 0.4: the uploaded avatar |
| `bio` | varchar(280), null | Same double-layer length protection as display_name |
| `account_status` | varchar(16) | active/suspended/deleted |
| `created_at`, `updated_at` | timestamptz | |

## `profiles_privacysettings`

| Column | Type | Notes |
|---|---|---|
| `profile_id` | uuid, PK, FK → profiles_profile, cascade delete | |
| `is_private_account` | bool, default true | Stored but inert — same 0.1-era decision, unchanged rationale (ADR-0014) |
| `created_at`, `updated_at` | timestamptz | |

## `posts_post` (0.2)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `author_id` | uuid FK → profiles_profile, cascade | index `(author_id, created_at DESC)` |
| `body` | varchar(500) | CHECK `body ~ '\S'` (non-blank) |
| `created_at` | timestamptz, indexed | |

## `follows_follow` (0.2)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `follower_id`, `following_id` | uuid FK → profiles_profile, cascade | UNIQUE pair; CHECK follower ≠ following |
| `status` | varchar(16) | `pending` / `accepted`; index `(following_id, status)` |
| `created_at` | timestamptz | |

## `safety_block` / `safety_report` (0.3)
| Table | Columns | Notes |
|---|---|---|
| `safety_block` | id uuid PK, blocker_id, blocked_id → profiles_profile (cascade), created_at | UNIQUE pair; CHECK blocker ≠ blocked |
| `safety_report` | id uuid PK, reporter_id → profiles_profile (cascade), target_type (user/post/comment), target_id uuid (NOT a FK), reason, details varchar(500), status (open/reviewing/actioned/dismissed), created_at, reviewed_at | UNIQUE (reporter, target_type, target_id); index (status, created_at) |

## `engagement_postlike` / `engagement_comment` (0.3)
| Table | Columns | Notes |
|---|---|---|
| `engagement_postlike` | id uuid PK, post_id → posts_post, profile_id → profiles_profile (cascade), created_at | UNIQUE (post, profile) |
| `engagement_comment` | id uuid PK, post_id, author_id (cascade), body varchar(300), created_at | CHECK non-blank; index (post, created_at DESC) |

## `media_image` (0.4)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `owner_id` | uuid FK → profiles_profile, cascade | index `(owner_id, created_at)` |
| `kind` | varchar(16) | `avatar` / `post` |
| `path`, `thumb_path` | varchar(255) | storage keys (re-encoded JPEGs) |
| `width`, `height`, `size_bytes` | int | of the full variant |
| `created_at` | timestamptz | |

`posts_post.image_id` (uuid, unique, null, SET NULL) → media_image: one image per post.

## `notifications_notification` (0.5)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `recipient_id`, `actor_id` | uuid FK → profiles_profile, cascade | CHECK recipient ≠ actor |
| `type` | varchar(24) | follow / follow_request / follow_accepted / like / comment |
| `post_id`, `comment_id` | uuid FK, null, cascade | |
| `created_at`, `read_at` | timestamptz (read_at null = unread) | indexes `(recipient, created_at DESC)`, `(recipient, read_at)` |

## Compliance tables (0.5.3)
| Table | Columns | Notes |
|---|---|---|
| `accounts_agerecord` | id uuid PK, user_id (1:1, cascade), `birth_year`, `birth_month`, `minimum_age_applied`, `rule_version`, `checked_at` | **no day of birth**; CHECK month 1–12, year 1900–2200; not in admin/serializers |
| `securitylog_securityevent` | id uuid PK, user_id (null, cascade), `event_type`, `ip_prefix` (/24 or /48), `user_agent_family`, `created_at` (indexed) | index (user, created_at DESC); purged after the retention period; no credentials/e-mail/full IP |
| `mailing_emailpreference` | id uuid PK, user_id (1:1, cascade), `marketing_opt_in` (default false), `marketing_source`, `marketing_updated_at` | |
| `mailing_emailsuppression` | id uuid PK, `email_hash` (unique, HMAC-SHA256), `reason`, `created_at` | the address itself is not stored |

## Relationships

```
accounts_user  →(1:1, cascade)→  profiles_profile  →(1:1, cascade)→  profiles_privacysettings
                                   profiles_profile  →(1:N, cascade)→  posts_post
                                   profiles_profile  ←(N:N via follows_follow, cascade)→  profiles_profile
```

## Row creation

`accounts.signals.create_profile_for_new_user` (a `post_save` signal on
`User`, same transaction) replaces the Postgres `SECURITY DEFINER` trigger —
same collision-safe placeholder-username logic (`user_` + 8 hex chars of the
UUID), same atomicity guarantee (Django's signal for a newly-created row
fires synchronously within the caller's transaction).

## Verification status

Schema **design validated live** against real PostgreSQL (the `veya-dev`
project, repurposed as plain Postgres) by hand-translating the Django models
into their exact generated DDL and testing constraints + cascade delete
directly — then removed, since Django's own migration executor must create
the real tables so its migration-state tracking stays consistent. The
**migration files themselves are hand-written**, not generated by
`manage.py makemigrations` (no Django installed in this environment — no
network to install it) — flagged for verification with
`makemigrations --check` in a real Django environment before being fully
trusted.
