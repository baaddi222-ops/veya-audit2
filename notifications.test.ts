import { describeNotification } from '../notifications/types';

describe('describeNotification', () => {
  it('describes each type', () => {
    expect(describeNotification({ type: 'follow', commentText: null })).toBe('started following you');
    expect(describeNotification({ type: 'follow_request', commentText: null })).toBe('requested to follow you');
    expect(describeNotification({ type: 'follow_accepted', commentText: null })).toBe('accepted your follow request');
    expect(describeNotification({ type: 'like', commentText: null })).toBe('liked your post');
  });
  it('includes the comment text when present', () => {
    expect(describeNotification({ type: 'comment', commentText: 'nice' })).toContain('nice');
    expect(describeNotification({ type: 'comment', commentText: null })).toBe('commented on your post');
  });
});
