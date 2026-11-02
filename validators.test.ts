// STATUS: WRITTEN, NOT EXECUTED — no network in this container to
// `npm install` Jest/Expo test deps. Run with `npm test` once installed.
import { validateBio, validateDisplayName, validateUsername } from '../profile/validators';

describe('validateUsername', () => {
  it('accepts a valid username', () => expect(validateUsername('valid_user_1')).toBeNull());
  it('rejects empty', () => expect(validateUsername('')).not.toBeNull());
  it('rejects too short', () => expect(validateUsername('ab')).not.toBeNull());
  it('rejects too long', () => expect(validateUsername('a'.repeat(25))).not.toBeNull());
  it('accepts boundary length 24', () => expect(validateUsername('a'.repeat(24))).toBeNull());
  it('rejects uppercase', () => expect(validateUsername('UPPER1')).not.toBeNull());
  it('rejects SQL-injection-shaped input', () =>
    expect(validateUsername("robert'); drop table x;--")).not.toBeNull());
});

describe('validateDisplayName', () => {
  it('null/empty is valid', () => expect(validateDisplayName('')).toBeNull());
  it('boundary 50 accepted', () => expect(validateDisplayName('a'.repeat(50))).toBeNull());
  it('51 rejected', () => expect(validateDisplayName('a'.repeat(51))).not.toBeNull());
  it('unicode under limit accepted', () => expect(validateDisplayName('محمد 😀 José')).toBeNull());
});

describe('validateBio', () => {
  it('boundary 280 accepted', () => expect(validateBio('a'.repeat(280))).toBeNull());
  it('281 rejected', () => expect(validateBio('a'.repeat(281))).not.toBeNull());
});
