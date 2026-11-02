# ADR-0025: In-app notifications (polling), no push yet
Date: 2026-10-07 · Status: Accepted · Release: VEYA 0.5

## Decision
`Notification(recipient, actor, type, post?, comment?, created_at, read_at)`; types: `follow`, `follow_request`,
`follow_accepted`, `like`, `comment`. Created explicitly by the views through `notifications.services.notify()`
(not by DB signals), so every trigger is visible in the code that causes it.

## Rules (all in `notify()` / the views)
* Never for yourself, never to a non-active account, never across a block (either direction).
* Idempotent per (recipient, actor, type, post, comment): toggling like/unlike or follow/unfollow does not spam.
* A resolved follow request (accepted or declined) or a cancelled request removes its `follow_request` notification;
  accepting additionally notifies the follower (`follow_accepted`).
* Blocking deletes all notifications between the two accounts, both ways. Deleting a post/comment cascades.
* Reads always start from the caller's own rows (`recipient = request.user's profile`) minus blocked/inactive actors;
  another user's notification id is a 404. Previews are only of the recipient's own post / comments on it.

## Mobile
"Alerts" tab with an unread badge; the count is polled every 30 s. Tapping a row marks it read and navigates
(comment/like → post comments, request → Requests, otherwise → actor's profile).

## Not in 0.5 (deliberately)
Push notifications (needs device-token registration + Expo/FCM credentials), realtime delivery, per-type settings,
notification grouping ("5 people liked…"), message/story/verification types.
