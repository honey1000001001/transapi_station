import client from './client';

export interface UsageStats {
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_prompt_tokens?: number;
  total_completion_tokens?: number;
  reasoning_tokens: number;
  daily_stats?: any[];
}

export interface RequestLog {
  id: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  reasoning_tokens: number;
  cost: number;
  latency_ms: number;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface LogsResponse {
  items: RequestLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface BalanceInfo {
  balance: number;
  total_recharged?: number;
  total_consumed?: number;
}

export interface RechargeRequest {
  code: string;
}

export interface RechargeResponse {
  amount: number;
  new_balance?: number;
  balance?: number;
}

export interface Invoice {
  period: string;
  total_requests: number;
  total_tokens: number;
  total_cost: number;
}

export async function getUsage(startDate?: string, endDate?: string): Promise<UsageStats> {
  const params: Record<string, string> = {};
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const res = await client.get<UsageStats>('/billing/usage', { params });
  return res.data;
}

export async function getLogs(
  page: number = 1,
  pageSize: number = 20,
  startDate?: string,
  endDate?: string
): Promise<LogsResponse | RequestLog[]> {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const res = await client.get('/billing/logs', { params });
  return res.data;
}

export async function getBalance(): Promise<BalanceInfo> {
  const res = await client.get<BalanceInfo>('/billing/balance');
  return res.data;
}

export async function recharge(data: RechargeRequest): Promise<RechargeResponse> {
  const res = await client.post<RechargeResponse>('/billing/recharge', data);
  return res.data;
}

export async function getInvoices(
  period: 'daily' | 'weekly' | 'monthly' = 'daily',
  startDate?: string,
  endDate?: string
): Promise<Invoice[]> {
  const params: Record<string, string> = { period };
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const res = await client.get<Invoice[]>('/billing/invoices', { params });
  return res.data;
}
