import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useUserId } from '../../shared/useUserId';
import { PickedImage, uploadImage } from '../../media/api';
import { postsApi } from '../api';

export function useFeed() {
  const userId = useUserId();
  return useInfiniteQuery({
    queryKey: ['feed', userId],
    queryFn: ({ pageParam }) => postsApi.feed(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor,
    enabled: userId !== null,
  });
}

export function useUserPosts(username: string, enabled: boolean) {
  const userId = useUserId();
  return useInfiniteQuery({
    queryKey: ['userPosts', userId, username],
    queryFn: ({ pageParam }) => postsApi.byUser(username, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor,
    enabled: userId !== null && enabled,
  });
}

export function useCreatePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ body, image }: { body: string; image?: PickedImage | null }) => {
      // upload first (server validates + re-encodes), then attach by id
      const imageId = image ? (await uploadImage('post', image)).id : undefined;
      return postsApi.create(body, imageId);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['feed'] });
      qc.invalidateQueries({ queryKey: ['userPosts'] });
    },
  });
}

export function useDeletePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => postsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['feed'] });
      qc.invalidateQueries({ queryKey: ['userPosts'] });
    },
  });
}

function refreshPosts(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['feed'] });
  qc.invalidateQueries({ queryKey: ['userPosts'] });
}

export function useToggleLike() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, liked }: { id: string; liked: boolean }) => postsApi.setLiked(id, liked),
    onSuccess: () => refreshPosts(qc),
  });
}

export function useComments(postId: string) {
  const userId = useUserId();
  return useInfiniteQuery({
    queryKey: ['comments', userId, postId],
    queryFn: ({ pageParam }) => postsApi.comments(postId, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor,
    enabled: userId !== null,
  });
}

export function useAddComment(postId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => postsApi.addComment(postId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['comments'] });
      refreshPosts(qc);
    },
  });
}

export function useDeleteComment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => postsApi.removeComment(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['comments'] });
      refreshPosts(qc);
    },
  });
}
