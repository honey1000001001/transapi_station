import { useEffect } from 'react';
import { useAuthStore } from '../stores/auth';
import { getMe } from '../api/auth';

export function useUser() {
  const { user, setUser } = useAuthStore();

  useEffect(() => {
    if (useAuthStore.getState().token && !user) {
      getMe()
        .then((u) => setUser(u))
        .catch(() => {});
    }
  }, []);

  return { user, refreshUser: () => getMe().then((u) => setUser(u)) };
}
