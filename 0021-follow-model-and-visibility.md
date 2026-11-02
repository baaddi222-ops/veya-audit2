# ADR-0021: Follow model, private-by-default visibility, single rules module
Date: 2026-10-02 · Status: Accepted · Release: VEYA 0.2

## Decision
* `Follow(follower → following, status pending|accepted)`, unique pair, DB CHECK
  forbidding self-follow.
* Accounts are private by default (`PrivacySettings.is_private_account=True`, from
  0.1). Following a private account creates a PENDING row; only the target can
  accept (queryset scoped to `following = request.user's profile`) or decline.
* ALL cross-user visibility lives in `follows/services.py` (`can_view_content`,
  `visible_posts`, `feed_posts`). Views never write their own visibility filters.

## Why
With no RLS backstop (ADR-0019), scattering visibility logic across views is how a
leak ships. One small module is auditable and testable.

## Behaviour notes (deliberate)
* Feed = own + accepted-followed accounts only. No discovery feed in 0.2.
* Re-following is idempotent and never upgrades a pending row.
* Switching an account from private to public does NOT auto-accept pending
  requests (they stay pending until decided). Revisit in 0.3.
* Suspended/deleted accounts' content is invisible to everyone else.
* Counts (followers/following) are shown even for private accounts; bio and post
  count are hidden from non-followers.
* No blocking yet (0.3+).
