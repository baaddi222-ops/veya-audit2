import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useUserId } from '../shared/useUserId';
import { mailingApi } from './api';

export function useMailPreferences() {
  const userId = useUserId();
  return useQuery({ queryKey: ['mailPrefs', userId], queryFn: mailingApi.get, enabled: userId !== null });
}

export function useSetMarketing() {
  const qc = useQueryClient();
  const userId = useUserId();
  return useMutation({
    mutationFn: (value: boolean) => mailingApi.setMarketing(value),
    onSuccess: (data) => qc.setQueryData(['mailPrefs', userId], data),
  });
}
