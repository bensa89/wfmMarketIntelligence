import { getCurrentUser, type CurrentUser } from '../api/client';

interface CurrentUserState {
  id: number;
  username: string;
  role: 'admin' | 'user';
  isAdmin: boolean;
}

export function useCurrentUser(): CurrentUserState | null {
  const user: CurrentUser | null = getCurrentUser();
  if (!user) return null;
  return { ...user, isAdmin: user.role === 'admin' };
}
