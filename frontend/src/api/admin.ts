import client from './client';
import type { User } from '../stores/auth';

// Admin user management
export interface AdminUser {
  id: string;
  username: string;
  email: string;
  role: 'user' | 'admin';
  balance: number;
  is_active: boolean;
  created_at: string;
}

export interface AdminUsersResponse {
  items: AdminUser[];
  total: number;
  page: number;
  page_size: number;
}

export interface UpdateUserRequest {
  role?: 'user' | 'admin';
  balance?: number;
  is_active?: boolean;
}

export async function listUsers(
  page: number = 1,
  pageSize: number = 20,
  search?: string
): Promise<AdminUser[] | AdminUsersResponse> {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (search) params.search = search;
  const res = await client.get('/admin/users', { params });
  return res.data;
}

export async function updateUser(id: string, data: UpdateUserRequest): Promise<AdminUser> {
  const res = await client.patch<AdminUser>(`/admin/users/${id}`, data);
  return res.data;
}

export async function deleteUser(id: string): Promise<void> {
  await client.delete(`/admin/users/${id}`);
}

// Upstream accounts
export interface UpstreamAccount {
  id: string;
  email: string;
  mobile: string | null;
  has_password: boolean;
  has_token: boolean;
  auth_mode: 'pool' | 'direct' | 'unknown';
  status: 'active' | 'disabled' | 'error';
  health: 'healthy' | 'degraded' | 'down';
  weight: number;
  total_requests: number;
  last_used_at: string | null;
  last_error: string | null;
  token_preview: string | null;
  created_at: string;
}

export interface UpstreamAccountsResponse {
  items: UpstreamAccount[];
  total: number;
}

export interface CreateUpstreamRequest {
  email: string;
  mobile?: string;
  password?: string;
  token?: string;
  weight?: number;
}

export interface UpdateUpstreamRequest {
  email?: string;
  mobile?: string;
  password?: string;
  token?: string;
  status?: string;
  weight?: number;
}

export async function listUpstreamAccounts(): Promise<UpstreamAccount[] | UpstreamAccountsResponse> {
  const res = await client.get('/admin/upstream-accounts');
  return res.data;
}

export async function createUpstreamAccount(data: CreateUpstreamRequest): Promise<UpstreamAccount> {
  const res = await client.post<UpstreamAccount>('/admin/upstream-accounts', data);
  return res.data;
}

export async function updateUpstreamAccount(
  id: string,
  data: UpdateUpstreamRequest
): Promise<UpstreamAccount> {
  const res = await client.patch<UpstreamAccount>(`/admin/upstream-accounts/${id}`, data);
  return res.data;
}

export async function deleteUpstreamAccount(id: string): Promise<void> {
  await client.delete(`/admin/upstream-accounts/${id}`);
}

export async function checkUpstreamHealth(id: string): Promise<any> {
  const res = await client.post(`/admin/upstream-accounts/${id}/health-check`);
  return res.data;
}

export async function syncUpstreamAccounts(): Promise<{ synced: number; total_accounts: number; errors: string[] }> {
  const res = await client.post('/admin/upstream-accounts/sync');
  return res.data;
}

export async function validateUpstreamToken(token: string): Promise<{ valid: boolean; message: string }> {
  const res = await client.post('/admin/upstream-accounts/validate-token', { token });
  return res.data;
}

export async function triggerUpstreamLogin(id: string): Promise<any> {
  const res = await client.post(`/admin/upstream-accounts/${id}/login`);
  return res.data;
}

// Recharge codes
export interface RechargeCode {
  id: string;
  code: string;
  amount: number;
  status: string;
  used_by: string | null;
  used_at: string | null;
  created_at: string;
}

export interface RechargeCodesResponse {
  items: RechargeCode[];
  total: number;
}

export interface CreateRechargeCodesRequest {
  amount: number;
  quantity: number;
}

export interface CreateRechargeCodesResponse {
  codes: { code: string; amount: number }[];
  count: number;
}

export async function listRechargeCodes(
  page: number = 1,
  pageSize: number = 20,
  status?: string
): Promise<RechargeCode[] | RechargeCodesResponse> {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (status) params.status = status;
  const res = await client.get('/admin/recharge-codes', { params });
  return res.data;
}

export async function createRechargeCodes(data: CreateRechargeCodesRequest): Promise<CreateRechargeCodesResponse> {
  const res = await client.post<CreateRechargeCodesResponse>('/admin/recharge-codes', data);
  return res.data;
}

// Rate limits
export interface RateLimitConfig {
  id: string;
  scope: 'global' | 'user' | 'key';
  target_id: string | null;
  rpm: number;
  tpm: number;
}

export async function getRateLimits(): Promise<RateLimitConfig[]> {
  const res = await client.get<RateLimitConfig[]>('/admin/rate-limits');
  return res.data;
}

export async function updateRateLimit(id: string, data: Partial<Pick<RateLimitConfig, 'rpm' | 'tpm'>>): Promise<RateLimitConfig> {
  const res = await client.patch<RateLimitConfig>(`/admin/rate-limits/${id}`, data);
  return res.data;
}

export async function createRateLimit(data: Omit<RateLimitConfig, 'id'>): Promise<RateLimitConfig> {
  const res = await client.post<RateLimitConfig>('/admin/rate-limits', data);
  return res.data;
}

// Stats
export interface SystemStats {
  total_users: number;
  active_users: number;
  total_requests: number;
  total_tokens: number;
  total_revenue: number;
  total_balance: number;
  active_keys: number;
  active_upstream_accounts: number;
}

export async function getStats(): Promise<SystemStats> {
  const res = await client.get<SystemStats>('/admin/stats');
  return res.data;
}

// Payments
export interface Payment {
  id: string;
  user_id: string;
  amount: number;
  method: string;
  status: string;
  ref_id: string | null;
  created_at: string;
}

export interface PaymentsResponse {
  items: Payment[];
  total: number;
  page: number;
  page_size: number;
}

export async function listPayments(
  page: number = 1,
  pageSize: number = 20
): Promise<Payment[] | PaymentsResponse> {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  const res = await client.get('/admin/payments', { params });
  return res.data;
}
