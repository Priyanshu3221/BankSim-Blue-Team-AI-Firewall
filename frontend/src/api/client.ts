/* Central API Client for BankSim */

import type {
  AdminDashboardMetrics,
  AIThreatAnalysisResponse,
  Account,
  CustomerTransactionListResponse,
  DevOtpResponse,
  LoginChallengeResponse,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  ResendOtpRequest,
  ResendOtpResponse,
  RiskAssessmentResponse,
  SecurityEventItem,
  TransferRequest,
  TransferResponse,
  User,
  VerifyChallengeRequest,
  VerifyChallengeResponse,
  VerifyLoginOtpRequest,
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('banksim_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = `${API_BASE_URL}${endpoint}`;
  let response: Response;

  try {
    response = await fetch(url, { ...options, headers });
  } catch (err: any) {
    throw new ApiError(0, 'Network connection failure: Cannot reach BankSim backend service.', err);
  }

  if (response.status === 401) {
    // If token expired, clear auth session
    localStorage.removeItem('banksim_token');
    localStorage.removeItem('banksim_user');
  }

  let data: any;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    const message =
      (data && typeof data === 'object' && data.detail && typeof data.detail === 'string'
        ? data.detail
        : data && typeof data === 'object' && data.detail && data.detail.message
        ? data.detail.message
        : null) ||
      `Request failed with status ${response.status}`;

    throw new ApiError(response.status, message, data?.detail || data);
  }

  return data as T;
}

export const api = {
  // Auth
  register: (payload: RegisterRequest): Promise<RegisterResponse> =>
    request<RegisterResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  login: (username: string, password: string): Promise<LoginChallengeResponse> =>
    request<LoginChallengeResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  verifyLoginOtp: (payload: VerifyLoginOtpRequest): Promise<LoginResponse> =>
    request<LoginResponse>('/auth/verify-otp', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  resendLoginOtp: (payload: ResendOtpRequest): Promise<ResendOtpResponse> =>
    request<ResendOtpResponse>('/auth/resend-otp', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getDevOtp: (challengeId: number): Promise<DevOtpResponse> =>
    request<DevOtpResponse>(`/auth/dev-otp/${challengeId}`),

  // Users
  getCurrentUser: (): Promise<User> => request<User>('/users/me'),

  // Banking
  getAccounts: (): Promise<Account[]> => request<Account[]>('/banking/accounts'),

  getTransactions: (params?: {
    account_id?: number;
    type?: string;
    status?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<CustomerTransactionListResponse> => {
    const query = new URLSearchParams();
    if (params?.account_id) query.append('account_id', params.account_id.toString());
    if (params?.type && params.type !== 'ALL') query.append('type', params.type);
    if (params?.status && params.status !== 'ALL') query.append('status', params.status);
    if (params?.search) query.append('search', params.search);
    if (params?.limit) query.append('limit', params.limit.toString());
    if (params?.offset !== undefined) query.append('offset', params.offset.toString());
    const qs = query.toString();
    return request<CustomerTransactionListResponse>(`/banking/transactions${qs ? `?${qs}` : ''}`);
  },

  transferFunds: (payload: TransferRequest): Promise<TransferResponse> =>
    request<TransferResponse>('/banking/transfer', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  verifyChallenge: (payload: VerifyChallengeRequest): Promise<VerifyChallengeResponse> =>
    request<VerifyChallengeResponse>('/banking/verify-challenge', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Security Console
  analyzeText: (text: string, contextType: string = 'transaction_memo'): Promise<AIThreatAnalysisResponse> =>
    request<AIThreatAnalysisResponse>('/security/analyze-text', {
      method: 'POST',
      body: JSON.stringify({ text, context_type: contextType }),
    }),

  assessRisk: (payload: {
    sender_account_id: number;
    recipient_account_number: string;
    amount_paise: number;
    memo?: string;
  }): Promise<RiskAssessmentResponse> =>
    request<RiskAssessmentResponse>('/security/assess-risk', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Admin
  getAdminDashboard: (): Promise<AdminDashboardMetrics> =>
    request<AdminDashboardMetrics>('/admin/dashboard'),

  getAdminSecurityEvents: (limit: number = 50): Promise<SecurityEventItem[]> =>
    request<SecurityEventItem[]>(`/admin/security-events?limit=${limit}`),
};
