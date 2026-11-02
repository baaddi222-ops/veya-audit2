/**
 * Date-of-birth entry helpers. IMPORTANT: this file validates only that the input is a REAL, non-future calendar
 * date. It deliberately does NOT know the minimum age — that is a server-side policy (settings.VEYA_MINIMUM_AGE) so it
 * can change without an app release and is never revealed to someone probing the form. The server decides.
 */
export interface DobParts {
  day: string;
  month: string;
  year: string;
}

export type DobFailure = 'incomplete' | 'invalid' | 'future';
export type DobResult = { ok: true; iso: string } | { ok: false; reason: DobFailure };

const pad = (n: number) => String(n).padStart(2, '0');

export function parseDateOfBirth(parts: DobParts, today: Date = new Date()): DobResult {
  const day = parts.day.trim();
  const month = parts.month.trim();
  const year = parts.year.trim();
  if (!day || !month || !year) return { ok: false, reason: 'incomplete' };
  if (!/^\d{1,2}$/.test(day) || !/^\d{1,2}$/.test(month) || !/^\d{4}$/.test(year)) return { ok: false, reason: 'invalid' };
  const d = Number(day);
  const m = Number(month);
  const y = Number(year);
  if (y < 1900) return { ok: false, reason: 'invalid' };
  const date = new Date(Date.UTC(y, m - 1, d));
  // rejects 31 Feb, 29 Feb in non-leap years, month 13, day 0 ... (Date.UTC would silently roll them over)
  if (date.getUTCFullYear() !== y || date.getUTCMonth() !== m - 1 || date.getUTCDate() !== d) {
    return { ok: false, reason: 'invalid' };
  }
  const todayUtc = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  if (date.getTime() > todayUtc) return { ok: false, reason: 'future' };
  return { ok: true, iso: `${y}-${pad(m)}-${pad(d)}` };
}

export function dobErrorMessage(reason: DobFailure): string {
  switch (reason) {
    case 'incomplete': return 'Enter your day, month and year of birth.';
    case 'future': return 'Enter a valid date of birth.';
    case 'invalid': return 'Enter a valid date of birth.';
  }
}
