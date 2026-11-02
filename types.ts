import { ProfileSummary } from '../posts/types';

export type NotificationType = 'follow' | 'follow_request' | 'follow_accepted' | 'like' | 'comment';

export interface AppNotification {
  id: string;
  type: NotificationType;
  actor: ProfileSummary;
  postId: string | null;
  postPreview: string | null;
  commentText: string | null;
  createdAt: string;
  read: boolean;
}

/** One-line description; the actor's @username is rendered separately in bold. */
export function describeNotification(n: Pick<AppNotification, 'type' | 'commentText'>): string {
  switch (n.type) {
    case 'follow': return 'started following you';
    case 'follow_request': return 'requested to follow you';
    case 'follow_accepted': return 'accepted your follow request';
    case 'like': return 'liked your post';
    case 'comment': return n.commentText ? `commented: “${n.commentText}”` : 'commented on your post';
  }
}
