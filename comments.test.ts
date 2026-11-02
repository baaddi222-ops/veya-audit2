import { MAX_COMMENT_LENGTH, validateCommentBody } from '../posts/types';

describe('validateCommentBody', () => {
  it('rejects empty / whitespace', () => {
    expect(validateCommentBody('')).not.toBeNull();
    expect(validateCommentBody('  \n')).not.toBeNull();
  });
  it('accepts the boundary', () => expect(validateCommentBody('a'.repeat(MAX_COMMENT_LENGTH))).toBeNull());
  it('rejects one over', () => expect(validateCommentBody('a'.repeat(MAX_COMMENT_LENGTH + 1))).not.toBeNull());
});
