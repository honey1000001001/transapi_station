import { useAuthStore } from '../stores/auth';

export function useAuth() {
  const { token, user, login, logout, isAdmin } = useAuthStore();
  return { token, user, login, logout, isAdmin: isAdmin(), isAuthenticated: !!token };
}
