import { cursorFromUrl, withCursor } from '../api/pagination';

describe('cursorFromUrl', () => {
  it('returns undefined for null', () => expect(cursorFromUrl(null)).toBeUndefined());
  it('extracts the cursor value', () =>
    expect(cursorFromUrl('http://x/api/feed/?cursor=cD0yMDI2&other=1')).toBe('cD0yMDI2'));
  it('decodes percent-encoding', () => expect(cursorFromUrl('http://x/?cursor=a%3Db')).toBe('a=b'));
});

describe('withCursor', () => {
  it('leaves path alone with no params', () => expect(withCursor('/feed/')).toBe('/feed/'));
  it('appends cursor', () => expect(withCursor('/feed/', 'abc')).toBe('/feed/?cursor=abc'));
  it('combines extra params and encodes them', () =>
    expect(withCursor('/users/search/', 'c', { q: 'a b' })).toBe('/users/search/?q=a%20b&cursor=c'));
});
