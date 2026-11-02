/**
 * React Query wraps loading/error/caching — the RN equivalent of
 * Riverpod's AsyncNotifier<Profile> from the Flutter phase. No optimistic
 * update on mutate (same 0.1-E §15 decision: wait for the confirmed server
 * result). Cache key is per-user via useAuth()'s userId, so signing out and
 * a different user signing in never shows a stale cached profile — the RN
 * re-expression of the 0.1-F "profile state bound to identity" fix.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../auth/AuthContext';
import { uploadImage, PickedImage } from '../../media/api';
import { profileApi } from '../api';
import { ProfileUpdate } from '../types';

export function useMyProfile() {
  const { state } = useAuth();
  const userId = state.kind === 'authenticated' ? state.userId : null;

  return useQuery({
    queryKey: ['profile', userId],
    queryFn: profileApi.getMyProfile,
    enabled: userId !== null,
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  const { state } = useAuth();
  const userId = state.kind === 'authenticated' ? state.userId : null;

  return useMutation({
    mutationFn: (update: ProfileUpdate) => profileApi.updateMyProfile(update),
    onSuccess: (profile) => {
      queryClient.setQueryData(['profile', userId], profile);
    },
  });
}

export function usePrivacy() {
  const userId = useUserIdForPrivacy();
  return useQuery({ queryKey: ['privacy', userId], queryFn: profileApi.getPrivacy, enabled: userId !== null });
}

export function useSetPrivate() {
  const queryClient = useQueryClient();
  const userId = useUserIdForPrivacy();
  return useMutation({
    mutationFn: (value: boolean) => profileApi.setPrivate(value),
    onSuccess: (data) => queryClient.setQueryData(['privacy', userId], data),
  });
}

function useUserIdForPrivacy(): string | null {
  const { state } = useAuth();
  return state.kind === 'authenticated' ? state.userId : null;
}

export function useSetAvatar() {
  const queryClient = useQueryClient();
  const userId = useUserIdForPrivacy();
  return useMutation({
    mutationFn: async (picked: PickedImage | null) => {
      if (picked === null) return profileApi.removeAvatar();
      const { id } = await uploadImage('avatar', picked);
      return profileApi.setAvatar(id);
    },
    onSuccess: (profile) => {
      queryClient.setQueryData(['profile', userId], profile);
      queryClient.invalidateQueries({ queryKey: ['feed'] });
      queryClient.invalidateQueries({ queryKey: ['userPosts'] });
    },
  });
}

export function useSubmitAge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dateOfBirth: string) => profileApi.submitAge(dateOfBirth),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['profile'] }),
  });
}
