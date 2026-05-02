import client from './client';
import type { User } from '../stores/auth';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export async function login(data: LoginRequest): Promise<LoginResponse> {
  const res = await client.post<LoginResponse>('/auth/login', data);
  return res.data;
}

export async function register(data: RegisterRequest): Promise<User> {
  const res = await client.post<User>('/auth/register', data);
  return res.data;
}

export async function getMe(): Promise<User> {
  const res = await client.get<User>('/auth/me');
  return res.data;
}
