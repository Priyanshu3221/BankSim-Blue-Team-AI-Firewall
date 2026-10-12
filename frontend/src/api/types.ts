/* BankSim TypeScript API Domain Types */

export interface User {
  id: number;
  username: string;
  email: string;
  role: 'USER' | 'ADMIN';
  is_active: boolean;
  created_at: string;
}

export interface Account {
  id: number;
  account_number: string;
  account_type: 'SAVINGS' | 'CURRENT';
  balance: number; // in paise (1 INR = 100 paise)
  currency: string;
  is_active: boolean;
  created_at: string;
}

export interface LoginChallengeResponse {
  status: 'OTP_REQUIRED';
  challenge_id: number;
  challenge_type: 'OTP';
  purpose: 'LOGIN';
  expires_in_seconds: number;
  cooldown_seconds: number;
  message: string;
}

export interface VerifyLoginOtpRequest {
  challenge_id: number;
  verification_code: string;
}

export interface ResendOtpRequest {
  challenge_id: number;
}

export interface ResendOtpResponse {
  status: 'OTP_RESENT';
  challenge_id: number;
  cooldown_seconds: number;
  expires_in_seconds: number;
  message: string;
}

export interface DevOtpResponse {
  challenge_id: number;
  dev_otp: string | null;
  environment: string;
  notice: string;
}

export interface RegisterRequest {
  full_name: string;
  email: string;
  phone_number: string;
  username: string;
  password: string;
  confirm_password: string;
}

export interface RegisterResponse {
  user_id: number;
  username: string;
  email: string;
  full_name?: string;
  account_number: string;
  initial_balance_inr: number;
  verification_status: string;
  message: string;
}

export interface CustomerTransactionItem {
  id: number;
  transaction_reference: string;
  direction: 'DEBIT' | 'CREDIT';
  amount_paise: number;
  amount_inr: number;
  status: string;
  description: string;
  memo?: string;
  counterparty_account?: string;
  created_at: string;
  sender_account_number?: string;
  recipient_account_number?: string;
}

export interface CustomerTransactionListResponse {
  total: number;
  limit: number;
  offset: number;
  items: CustomerTransactionItem[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id: number;
  role: string;
  user: User;
}

export interface TransferRequest {
  recipient_account_number: string;
  amount_paise: number;
  sender_account_id?: number;
  memo?: string;
  challenge_id?: number;
}

export interface TransferResponse {
  success: boolean;
  status: 'COMPLETED' | 'STEP_UP_REQUIRED' | 'BLOCKED' | 'FAILED';
  message: string;
  reference?: string;
  transaction_id?: number;
  amount_paise: number;
  sender_account_number: string;
  recipient_account_number: string;
  remaining_balance_paise?: number;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  recommended_outcome: 'ALLOW' | 'STEP_UP_VERIFICATION' | 'RESTRICT' | 'BLOCK';
  challenge_id?: number;
  challenge_type?: 'OTP' | 'FACE_VERIFICATION';
  executed_at: string;
}

export interface TransferStepUpError {
  status: 'STEP_UP_REQUIRED';
  message: string;
  risk_score: number;
  risk_level: string;
  recommended_outcome: string;
  challenge_id: number;
  challenge_type: 'OTP' | 'FACE_VERIFICATION';
  explanation: string;
}

export interface TransferBlockedError {
  status: 'BLOCKED';
  message: string;
  risk_score: number;
  risk_level: string;
  recommended_outcome: string;
  explanation: string;
}

export interface VerifyChallengeRequest {
  challenge_id: number;
  verification_code?: string;
  face_data?: string;
}

export interface VerifyChallengeResponse {
  challenge_id: number;
  status: 'VERIFIED' | 'FAILED' | 'EXPIRED';
  message: string;
}

export interface RiskSignalResult {
  signal_name: string;
  triggered: boolean;
  score_impact: number;
  description: string;
  evidence?: Record<string, any>;
  status: string;
}

export interface RiskAssessmentResponse {
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  recommended_outcome: 'ALLOW' | 'STEP_UP_VERIFICATION' | 'RESTRICT' | 'BLOCK';
  triggered_signals: RiskSignalResult[];
  all_signals: RiskSignalResult[];
  explanation: string;
  evaluated_at: string;
}

export interface AIThreatAnalysisResponse {
  threat_detected: boolean;
  threat_categories: string[];
  evidence: any[];
  confidence: number;
  recommended_action: 'ALLOW' | 'FLAG_FOR_REVIEW' | 'STEP_UP_VERIFICATION' | 'BLOCK';
  explanation: string;
  provider_used: string;
  analyzed_at: string;
}

export interface AdminDashboardMetrics {
  total_users: number;
  total_accounts: number;
  total_transactions: number;
  security_events_24h: number;
  high_risk_events_24h: number;
  system_status: string;
}

export interface SecurityEventItem {
  id: number;
  user_id?: number;
  event_type: 'LOGIN_FAILURE' | 'RATE_LIMIT' | 'THREAT_DETECTED' | 'TRANSACTION_BLOCKED' | 'STEP_UP_REQUIRED';
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string;
  risk_score?: number;
  request_id?: string;
  created_at: string;
}
