// Model names, prices, API paths
export const MODEL_PRICES: Record<string, { input: number; output: number; label: string }> = {
  'deepseek-chat': { input: 0.001, output: 0.002, label: 'DeepSeek Chat' },
  'deepseek-reasoner': { input: 0.002, output: 0.006, label: 'DeepSeek Reasoner' },
  'deepseek-chat-search': { input: 0.002, output: 0.004, label: 'DeepSeek Chat (搜索)' },
  'deepseek-reasoner-search': { input: 0.004, output: 0.012, label: 'DeepSeek Reasoner (搜索)' },
};

export const MODEL_LIST = Object.keys(MODEL_PRICES);

export const API_PATHS = {
  AUTH_REGISTER: '/auth/register',
  AUTH_LOGIN: '/auth/login',
  AUTH_ME: '/auth/me',
  KEYS: '/keys',
  KEY_BY_ID: (id: string) => `/keys/${id}`,
  BILLING_USAGE: '/billing/usage',
  BILLING_LOGS: '/billing/logs',
  BILLING_BALANCE: '/billing/balance',
  BILLING_RECHARGE: '/billing/recharge',
  BILLING_INVOICES: '/billing/invoices',
  PROXY_MODELS: '/models',
  ADMIN_USERS: '/admin/users',
  ADMIN_USER_BY_ID: (id: string) => `/admin/users/${id}`,
  ADMIN_RATE_LIMITS: '/admin/rate-limits',
  ADMIN_UPSTREAM_ACCOUNTS: '/admin/upstream-accounts',
  ADMIN_UPSTREAM_BY_ID: (id: string) => `/admin/upstream-accounts/${id}`,
  ADMIN_STATS: '/admin/stats',
  ADMIN_RECHARGE_CODES: '/admin/recharge-codes',
  ADMIN_PAYMENTS: '/admin/payments',
};

export const PAGE_SIZE = 20;

export const DATE_FORMAT = 'YYYY-MM-DD HH:mm:ss';
