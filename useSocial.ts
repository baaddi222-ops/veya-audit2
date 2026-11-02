import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useUserId } from '../../shared/useUserId';
import { socialApi } from '../api';

export function usePublicProfile(username: string) {
  const userId = useUserId();
  return useQuery({
    queryKey: ['publicProfile', userId, username],
    queryFn: () => socialApi.getUser(username),
    enabled: userId !== null,
  });
}

export function useToggleFollow(username: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (currentlyConnected: boolean) => {
      if (currentlyConnected) await socialApi.unfollow(username);
      else await socialApi.follow(username);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['publicProfile'] });
      qc.invalidateQueries({ queryKey: ['feed'] });
      qc.invalidateQueries({ queryKey: ['userPosts'] });
    },
  });
}

export function useUserSearch(q: string) {
  const userId = useUserId();
  const term = q.trim().toLowerCase();
  return useQuery({
    queryKey: ['userSearch', userId, term],
    queryFn: () => socialApi.search(term),
    enabled: userId !== null && term.length >= 2,
  });
}

export function useFollowRequests() {
  const userId = useUserId();
  return useInfiniteQuery({
    queryKey: ['followRequests', userId],
    queryFn: ({ pageParam }) => socialApi.requests(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor,
    enabled: userId !== null,
  });
}

export function useDecideRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'accept' | 'decline' }) => socialApi.decide(id, action),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['followRequests'] });
      qc.invalidateQueries({ queryKey: ['publicProfile'] });
      qc.invalidateQueries({ queryKey: ['notifications'] });
      qc.invalidateQueries({ queryKey: ['unreadCount'] });
    },
  });
}

export function useBlock(username: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (block: boolean) => {
      if (block) await socialApi.block(username);
      else await socialApi.unblock(username);
    },
    onSuccess: () => {
      // a block changes what every list may contain — drop all cached social data
      ['publicProfile', 'feed', 'userPosts', 'userSearch', 'followRequests', 'blocked', 'comments', 'notifications', 'unreadCount'].forEach((k) =>
        qc.invalidateQueries({ queryKey: [k] }),
      );
    },
  });
}

export function useBlockedUsers() {
  const userId = useUserId();
  return useQuery({ queryKey: ['blocked', userId], queryFn: socialApi.blocked, enabled: userId !== null });
}

export function useReport() {
  return useMutation({ mutationFn: socialApi.report });
}
