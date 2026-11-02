import { decodeUserId } from '../auth/AuthContext';

// JWT segments are base64URL: '-' and '_' instead of '+' and '/', and no '=' padding.
// A plain atob() throws on those characters (0.1 bug), so the payload below is built
// to force BOTH url-safe characters into the encoded segment.
function token(payload: object): string {
  const b64 = Buffer.from(JSON.stringify(payload)).toString('base64')
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  return `x.${b64}.y`;
}

describe('decodeUserId', () => {
  it('reads user_id', () => expect(decodeUserId(token({ user_id: 'abc-123' }))).toBe('abc-123'));

  it('handles url-safe characters and missing padding', () => {
    const t = token({ user_id: 'u', pad: '>>>>>>>>>>>>>>>???????????????' });
    const segment = t.split('.')[1] as string;
    expect(segment.includes('-')).toBe(true);   // test-setup guard: really url-safe
    expect(segment.includes('_')).toBe(true);
    expect(decodeUserId(t)).toBe('u');
  });

  it('coerces numeric ids to string', () => expect(decodeUserId(token({ user_id: 42 }))).toBe('42'));
});
