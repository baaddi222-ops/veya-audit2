# ADR-0024: Image uploads — validate, re-encode, store privately, serve by signed URL
Date: 2026-10-04 · Status: Accepted · Release: VEYA 0.4 (supersedes the "text-only" part of ADR-0020 and ADR-0013)

## Decision
* **Two-step flow.** `POST /api/media/` (multipart: `kind=post|avatar`, `file`) → `{id}`; the id is then attached:
  `POST /api/posts/ {body, image_id}` or `PUT /api/profile/me/avatar/ {image_id}`.
* **Never trust the upload.** Filename and client MIME are ignored. Pillow opens + verifies the bytes; only JPEG/PNG/WEBP
  are accepted (no GIF/SVG/HEIC/TIFF); size ≤ 5 MB; ≤ 40 MP (decompression-bomb guard).
* **Always re-encode** to JPEG (alpha flattened onto white, EXIF orientation applied). Re-encoding drops EXIF/GPS and any
  appended payload. Post: 1600 px full + 400 px thumb; avatar: 512 + 128. Originals are never stored.
* **Storage** goes through Django's `default_storage` (local disk in dev; point `STORAGES["default"]` at S3 etc. in prod — no code change).
  Files are named by random UUID under `images/<owner>/…`.
* **Not publicly mounted.** There is no `MEDIA_URL` static route. Files are served only by `GET /api/media/<id>/<full|thumb>/?s=<sig>`.
* **Signed URLs.** `sig = bucket.HMAC(SECRET_KEY, id:bucket)`; bucket = 6 h; valid for the current + previous bucket (6–12 h). Deterministic
  within a bucket so React Native's image cache works. URLs are only emitted inside API responses the viewer was already authorised to get
  (post visibility, block rules and account status apply first). Invalid/expired signature and unknown id are the same 404.
* **Ownership.** An image can only be attached by its uploader, only to the matching kind, and only once (OneToOne on posts).
  Someone else's id looks exactly like a nonexistent one. Max 20 unattached uploads per user; uploads throttled 30/h.
* **Lifecycle.** Deleting a post deletes its image row + files; replacing/removing an avatar deletes the old image;
  `manage.py cleanup_orphan_images --hours 24` removes never-attached uploads (run it from cron).
* **avatar_url is no longer client-writable.** Arbitrary URLs allowed tracking pixels / hotlinking. The column stays (deprecated);
  the avatar is the uploaded image.

## Trade-offs (deliberate)
* A signed URL is a bearer capability for ≤ 12 h: whoever holds it can fetch that single image. Accepted for RN image caching;
  the alternative (per-request tokens / auth headers on `<Image>`) breaks caching and refresh.
* Unattached uploads are private to the uploader but occupy storage until cleaned.
* Files are streamed through Django. For production move to presigned object-storage URLs / CDN (later phase).
* Post body is still required (a photo post needs a caption).
* No virus scanning; the re-encode removes any non-pixel payload, which is the relevant risk for images.
