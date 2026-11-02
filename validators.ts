/**
 * Shared, pure validators — direct port of profile_validators.dart. Mirror
 * the backend's constraints exactly (profiles/models.py); these are
 * UX-layer only, the backend remains authoritative (0.1-C/E principle,
 * restated for a stack with no RLS: the SERIALIZER's field list + these
 * DB-level CHECK constraints are the real boundary, not this file).
 */
export function validateUsername(value: string): string | null {
  const v = value.trim();
  if (v.length < 3 || v.length > 24) return 'Username must be 3-24 characters';
  if (!/^[a-z0-9_]+$/.test(v)) return 'Lowercase letters, numbers, and underscores only';
  return null;
}

export function validateDisplayName(value: string): string | null {
  if (!value.trim()) return null;
  if ([...value.trim()].length > 50) return 'Display name must be 50 characters or fewer';
  return null;
}

export function validateBio(value: string): string | null {
  if (!value.trim()) return null;
  if ([...value.trim()].length > 280) return 'Bio must be 280 characters or fewer';
  return null;
}
