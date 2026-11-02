export interface Page<T> {
  next: string | null;
  results: T[];
}

/** DRF CursorPagination returns a full `next` URL; the only thing the client
 *  needs from it is the opaque `cursor` query value. */
export function cursorFromUrl(next: string | null): string | undefined {
  if (!next) return undefined;
  const match = /[?&]cursor=([^&]+)/.exec(next);
  return match?.[1] ? decodeURIComponent(match[1]) : undefined;
}

export function withCursor(path: string, cursor?: string, extra: Record<string, string> = {}): string {
  const params = Object.entries(extra).map(([k, v]) => `${k}=${encodeURIComponent(v)}`);
  if (cursor) params.push(`cursor=${encodeURIComponent(cursor)}`);
  return params.length ? `${path}${path.includes('?') ? '&' : '?'}${params.join('&')}` : path;
}
