import { MAX_POST_LENGTH, validatePostBody } from '../posts/types';

describe('validatePostBody', () => {
  it('rejects empty and whitespace', () => {
    expect(validatePostBody('')).not.toBeNull();
    expect(validatePostBody('   \n ')).not.toBeNull();
  });
  it('accepts boundary length', () => expect(validatePostBody('a'.repeat(MAX_POST_LENGTH))).toBeNull());
  it('rejects one over', () => expect(validatePostBody('a'.repeat(MAX_POST_LENGTH + 1))).not.toBeNull());
  it('counts emoji / Arabic by code point', () => expect(validatePostBody('😀'.repeat(MAX_POST_LENGTH))).toBeNull());
});
