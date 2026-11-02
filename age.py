"""Age-gate arithmetic — PURE Python (no Django), so it can be unit-tested anywhere.

The minimum age is NOT decided here: it is a project policy value (settings.VEYA_MINIMUM_AGE) that the owner must set after
legal review per target market. Nothing in this file asserts what any law requires.
Leap-day rule: someone born on 29 Feb reaches a new age on 1 March in non-leap years (the conservative reading)."""
from datetime import date

OK = 'ok'
TOO_YOUNG = 'too_young'
FUTURE = 'future'
IMPLAUSIBLE = 'implausible'
MAX_PLAUSIBLE_AGE = 120


def age_on(dob: date, today: date) -> int:
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def evaluate(dob: date, today: date, minimum: int) -> str:
    """OK | TOO_YOUNG | FUTURE | IMPLAUSIBLE for a date of birth on `today` under policy `minimum` (whole years)."""
    if minimum < 0:
        raise ValueError('minimum age must be >= 0')
    if dob > today:
        return FUTURE
    age = age_on(dob, today)
    if age > MAX_PLAUSIBLE_AGE:
        return IMPLAUSIBLE
    if age < minimum:
        return TOO_YOUNG
    return OK
