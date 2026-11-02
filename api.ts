import { apiClient } from '../api/client';
import { cursorFromUrl, Page, withCursor } from '../api/pagination';
import { ProfileSummaryWire, summaryFromWire } from '../posts/api';
import { ProfileSummary } from '../posts/types';
import { FollowRequest, PublicProfile, Relationship } from './types';

interface PublicProfileWire extends ProfileSummaryWire {
  bio: string | null;
  is_private: boolean;
  relationship: Relationship;
  can_view_posts: boolean;
  follower_count: number;
  following_count: number;
  post_count: number;
}
interface FollowRequestWire {
  id: string;
  follower: ProfileSummaryWire;
  created_at: string;
}

const u = (username: string) => encodeURIComponent(username);

export const socialApi = {
  async getUser(username: string): Promise<PublicProfile> {
    const w = await apiClient.request<PublicProfileWire>(`/users/${u(username)}/`);
    return {
      ...summaryFromWire(w),
      bio: w.bio,
      isPrivate: w.is_private,
      relationship: w.relationship,
      canViewPosts: w.can_view_posts,
      followerCount: w.follower_count,
      followingCount: w.following_count,
      postCount: w.post_count,
    };
  },
  async follow(username: string): Promise<Relationship> {
    const r = await apiClient.request<{ relationship: Relationship }>(`/users/${u(username)}/follow/`, { method: 'POST' });
    return r.relationship;
  },
  async unfollow(username: string): Promise<void> {
    await apiClient.request(`/users/${u(username)}/follow/`, { method: 'DELETE' });
  },
  async search(q: string): Promise<ProfileSummary[]> {
    const page = await apiClient.request<Page<ProfileSummaryWire>>(withCursor('/users/search/', undefined, { q }));
    return page.results.map(summaryFromWire);
  },
  async requests(cursor?: string): Promise<{ items: FollowRequest[]; nextCursor?: string }> {
    const page = await apiClient.request<Page<FollowRequestWire>>(withCursor('/follows/requests/', cursor));
    return {
      items: page.results.map((r) => ({ id: r.id, follower: summaryFromWire(r.follower), createdAt: r.created_at })),
      nextCursor: cursorFromUrl(page.next),
    };
  },
  async block(username: string): Promise<void> {
    await apiClient.request(`/users/${u(username)}/block/`, { method: 'POST' });
  },
  async unblock(username: string): Promise<void> {
    await apiClient.request(`/users/${u(username)}/block/`, { method: 'DELETE' });
  },
  async blocked(): Promise<ProfileSummary[]> {
    const page = await apiClient.request<Page<{ id: string; user: ProfileSummaryWire }>>('/safety/blocks/');
    return page.results.map((b) => summaryFromWire(b.user));
  },
  async report(input: { targetType: 'user' | 'post' | 'comment'; targetId: string; reason: string; details?: string }): Promise<void> {
    await apiClient.request('/safety/reports/', {
      method: 'POST',
      body: { target_type: input.targetType, target_id: input.targetId, reason: input.reason, details: input.details ?? '' },
    });
  },
  async decide(id: string, action: 'accept' | 'decline'): Promise<void> {
    await apiClient.request(`/follows/requests/${id}/${action}/`, { method: 'POST' });
  },
};
