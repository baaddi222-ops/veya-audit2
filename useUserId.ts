import { useAuth } from '../auth/AuthContext';

/** Query keys are scoped by user id so one user's cache is never shown to the next. */
export function useUserId(): string | null {
  const { state } = useAuth();
  return state.kind === 'authenticated' ? state.userId : null;
}
