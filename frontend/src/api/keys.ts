import client from './client';

export interface ApiKey {
  id: string;
  key_prefix: string;
  name: string;
  is_active: boolean;
  rpm_limit: number;
  tpm_limit: number;
  total_requests: number;
  total_tokens: number;
  created_at: string;
}

export interface CreateKeyRequest {
  name: string;
  rpm_limit?: number;
  tpm_limit?: number;
}

export interface CreateKeyResponse {
  id: string;
  key: string;
  key_prefix: string;
  name: string;
}

export async function listKeys(): Promise<ApiKey[]> {
  const res = await client.get<ApiKey[]>('/keys');
  return res.data;
}

export async function createKey(data: CreateKeyRequest): Promise<CreateKeyResponse> {
  const res = await client.post<CreateKeyResponse>('/keys', data);
  return res.data;
}

export async function revokeKey(id: string): Promise<void> {
  await client.delete(`/keys/${id}`);
}

export async function updateKey(id: string, data: Partial<Pick<ApiKey, 'name' | 'rpm_limit' | 'tpm_limit' | 'is_active'>>): Promise<ApiKey> {
  const res = await client.patch<ApiKey>(`/keys/${id}`, data);
  return res.data;
}
