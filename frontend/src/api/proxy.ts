import client from './client';

export interface ModelInfo {
  id: string;
  object: string;
  owned_by: string;
}

export interface ModelsResponse {
  data: ModelInfo[];
}

export async function getModels(): Promise<ModelsResponse> {
  const res = await client.get<ModelsResponse>('/models');
  return res.data;
}
