import { dobErrorMessage, parseDateOfBirth } from '../auth/age';

const TODAY = new Date(2026, 9, 28); // 28 Oct 2026 (local)
const p = (day: string, month: string, year: string) => parseDateOfBirth({ day, month, year }, TODAY);

describe('parseDateOfBirth', () => {
  it('accepts real dates and returns an ISO string', () => {
    expect(p('15', '1', '1990')).toEqual({ ok: true, iso: '1990-01-15' });
    expect(p('01', '02', '2000')).toEqual({ ok: true, iso: '2000-02-01' });
  });
  it('accepts today (the server decides about age)', () => expect(p('28', '10', '2026')).toEqual({ ok: true, iso: '2026-10-28' }));
  it('accepts 29 Feb only in leap years', () => {
    expect(p('29', '2', '2000')).toEqual({ ok: true, iso: '2000-02-29' });
    expect(p('29', '2', '2001')).toEqual({ ok: false, reason: 'invalid' });
    expect(p('29', '2', '1900')).toEqual({ ok: false, reason: 'invalid' });
  });
  it('rejects impossible calendar dates instead of rolling them over', () => {
    expect(p('31', '4', '1990')).toEqual({ ok: false, reason: 'invalid' });
    expect(p('0', '1', '1990')).toEqual({ ok: false, reason: 'invalid' });
    expect(p('1', '13', '1990')).toEqual({ ok: false, reason: 'invalid' });
    expect(p('32', '1', '1990')).toEqual({ ok: false, reason: 'invalid' });
  });
  it('rejects non-numeric, short years and signs', () => {
    expect(p('ab', '1', '1990')).toEqual({ ok: false, reason: 'invalid' });
    expect(p('1', '1', '90')).toEqual({ ok: false, reason: 'invalid' });
    expect(p('-1', '1', '1990')).toEqual({ ok: false, reason: 'invalid' });
    expect(p('1.5', '1', '1990')).toEqual({ ok: false, reason: 'invalid' });
    expect(p('1', '1', '19900')).toEqual({ ok: false, reason: 'invalid' });
  });
  it('rejects future dates and years before 1900', () => {
    expect(p('29', '10', '2026')).toEqual({ ok: false, reason: 'future' });
    expect(p('1', '1', '2999')).toEqual({ ok: false, reason: 'future' });
    expect(p('31', '12', '1899')).toEqual({ ok: false, reason: 'invalid' });
  });
  it('reports incomplete input', () => {
    expect(p('', '1', '1990')).toEqual({ ok: false, reason: 'incomplete' });
    expect(p(' ', ' ', ' ')).toEqual({ ok: false, reason: 'incomplete' });
  });
  it('never mentions a minimum age in any message', () => {
    for (const r of ['incomplete', 'invalid', 'future'] as const) {
      expect(/\d/.test(dobErrorMessage(r))).toBe(false);
    }
  });
});
