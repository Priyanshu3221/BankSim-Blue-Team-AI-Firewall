import React, { useEffect, useState } from 'react';
import {
  Shield,
  Lock,
  User as UserIcon,
  AlertCircle,
  ArrowRight,
  Eye,
  EyeOff,
  KeyRound,
  RefreshCw,
  ArrowLeft,
  Clock,
  CheckCircle2,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';

interface LoginPageProps {
  onSuccess: () => void;
  onNavigateToHome?: () => void;
  onNavigateToRegister?: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({
  onSuccess,
  onNavigateToHome,
  onNavigateToRegister,
}) => {
  const { initiateLogin, verifyLogin, resendLoginOtp } = useAuth();

  // Step state
  const [step, setStep] = useState<'CREDENTIALS' | 'OTP'>('CREDENTIALS');

  // Credentials form state
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // OTP state
  const [challengeId, setChallengeId] = useState<number | null>(null);
  const [otpCode, setOtpCode] = useState('');
  const [devOtp, setDevOtp] = useState<string | null>(null);
  const [cooldownSeconds, setCooldownSeconds] = useState<number>(0);
  const [expirySeconds, setExpirySeconds] = useState<number>(0);
  const [attemptCount, setAttemptCount] = useState<number>(0);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  // UI state
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  // Cooldown countdown timer
  useEffect(() => {
    if (cooldownSeconds <= 0) return;
    const timer = setInterval(() => {
      setCooldownSeconds((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldownSeconds]);

  // Expiry countdown timer
  useEffect(() => {
    if (expirySeconds <= 0) return;
    const timer = setInterval(() => {
      setExpirySeconds((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [expirySeconds]);

  // Fetch simulated dev mailbox OTP in development/demo mode
  const fetchDevMailboxOtp = async (chId: number) => {
    try {
      const res = await api.getDevOtp(chId);
      if (res && res.dev_otp) {
        setDevOtp(res.dev_otp);
      }
    } catch {
      // In production or if dev endpoint is not accessible, silently skip
      setDevOtp(null);
    }
  };

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Please provide both username and password.');
      return;
    }

    setError(null);
    setInfoMessage(null);
    setLoading(true);

    try {
      const res = await initiateLogin(username.trim(), password);
      if (res.status === 'OTP_REQUIRED') {
        setChallengeId(res.challenge_id);
        setExpirySeconds(res.expires_in_seconds || 300);
        setCooldownSeconds(res.cooldown_seconds || 30);
        setAttemptCount(0);
        setOtpCode('');
        setStep('OTP');
        // Fetch test OTP for demo simulation
        fetchDevMailboxOtp(res.challenge_id);
      } else {
        setError('Unexpected authentication state.');
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!challengeId) return;

    const trimmedCode = otpCode.trim();
    if (trimmedCode.length !== 6) {
      setError('Please enter a valid 6-digit verification code.');
      return;
    }

    setError(null);
    setInfoMessage(null);
    setLoading(true);

    try {
      await verifyLogin(challengeId, trimmedCode);
      onSuccess();
    } catch (err: any) {
      setAttemptCount((prev) => prev + 1);
      setError(err.message || 'Invalid verification code.');
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    if (!challengeId || cooldownSeconds > 0 || resending) return;

    setError(null);
    setInfoMessage(null);
    setResending(true);

    try {
      const res = await resendLoginOtp(challengeId);
      setCooldownSeconds(res.cooldown_seconds || 30);
      setExpirySeconds(res.expires_in_seconds || 300);
      setInfoMessage('A new verification code has been dispatched.');
      setOtpCode('');
      // Refresh dev mailbox code
      fetchDevMailboxOtp(challengeId);
    } catch (err: any) {
      setError(err.message || 'Failed to resend verification code.');
    } finally {
      setResending(false);
    }
  };

  const handleDemoFill = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
    setError(null);
  };

  const handleBackToCredentials = () => {
    setStep('CREDENTIALS');
    setChallengeId(null);
    setOtpCode('');
    setError(null);
    setInfoMessage(null);
    setDevOtp(null);
  };

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  return (
    <div
      style={{
        minHeight: '80vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.5rem 1rem',
        backgroundColor: 'var(--color-page-bg)',
      }}
    >
      <div
        className="card"
        style={{
          maxWidth: '420px',
          width: '100%',
          padding: '2rem',
        }}
      >
        {/* Header */}
        {onNavigateToHome && (
          <button
            type="button"
            onClick={onNavigateToHome}
            style={{
              background: 'none',
              border: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              color: 'var(--color-text-secondary)',
              fontSize: '0.75rem',
              cursor: 'pointer',
              marginBottom: '1rem',
              padding: 0,
            }}
          >
            <ArrowLeft size={14} />
            <span>Back to BankSim Home</span>
          </button>
        )}
        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '4px',
              backgroundColor: 'var(--color-primary-burgundy)',
              margin: '0 auto 0.75rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {step === 'CREDENTIALS' ? (
              <Shield size={20} color="#FFFFFF" />
            ) : (
              <KeyRound size={20} color="#FFFFFF" />
            )}
          </div>
          <h1
            style={{
              fontSize: '1.25rem',
              fontWeight: 600,
              color: 'var(--color-text-main)',
              marginBottom: '0.25rem',
            }}
          >
            {step === 'CREDENTIALS' ? 'BankSim Sign In' : 'Two-Factor Authentication'}
          </h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.8125rem' }}>
            {step === 'CREDENTIALS'
              ? 'Enter your credentials to access the banking portal'
              : 'Mandatory verification required for all user and admin accounts'}
          </p>
        </div>

        {/* Status Messages */}
        {error && (
          <div className="alert-box alert-box-danger" style={{ marginBottom: '1rem' }}>
            <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <div style={{ fontSize: '0.8125rem', fontWeight: 600 }}>Authentication Error</div>
              <div style={{ fontSize: '0.75rem', marginTop: '0.15rem' }}>{error}</div>
              {step === 'OTP' && attemptCount > 0 && attemptCount < 3 && (
                <div style={{ fontSize: '0.6875rem', marginTop: '0.25rem', color: 'var(--color-warning)' }}>
                  Failed attempts: {attemptCount} / 3. Challenge locks on 3rd failure.
                </div>
              )}
            </div>
          </div>
        )}

        {infoMessage && (
          <div className="alert-box alert-box-success" style={{ marginBottom: '1rem' }}>
            <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
            <div style={{ fontSize: '0.8125rem' }}>{infoMessage}</div>
          </div>
        )}

        {/* STEP 1: CREDENTIALS */}
        {step === 'CREDENTIALS' && (
          <>
            <form onSubmit={handleCredentialsSubmit}>
              <div className="form-group">
                <label className="form-label" htmlFor="username">
                  Username
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    id="username"
                    type="text"
                    className="form-input"
                    placeholder="Enter username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="username"
                    style={{ paddingLeft: '2.25rem' }}
                    disabled={loading}
                  />
                  <UserIcon
                    size={15}
                    color="var(--color-text-secondary)"
                    style={{
                      position: 'absolute',
                      left: '0.75rem',
                      top: '50%',
                      transform: 'translateY(-50%)',
                    }}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="password">
                  Password
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    className="form-input"
                    placeholder="Enter password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    style={{ paddingLeft: '2.25rem', paddingRight: '2.25rem' }}
                    disabled={loading}
                  />
                  <Lock
                    size={15}
                    color="var(--color-text-secondary)"
                    style={{
                      position: 'absolute',
                      left: '0.75rem',
                      top: '50%',
                      transform: 'translateY(-50%)',
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute',
                      right: '0.625rem',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: 'var(--color-text-secondary)',
                      display: 'flex',
                      alignItems: 'center',
                      padding: '0.25rem',
                    }}
                    title={showPassword ? 'Hide password' : 'Show password'}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '0.35rem', padding: '0.55rem' }}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <RefreshCw size={14} className="spin" /> Verifying Credentials...
                  </>
                ) : (
                  <>
                    Continue to OTP Verification <ArrowRight size={14} />
                  </>
                )}
              </button>
            </form>

            {/* Demo Fast Fill */}
            <div
              style={{
                marginTop: '1.5rem',
                paddingTop: '1rem',
                borderTop: '1px solid var(--color-border)',
                textAlign: 'center',
              }}
            >
              <div
                style={{
                  fontSize: '0.6875rem',
                  color: 'var(--color-text-secondary)',
                  marginBottom: '0.5rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                  fontWeight: 600,
                }}
              >
                Demo Account Credentials
              </div>
              <div
                style={{
                  display: 'flex',
                  gap: '0.35rem',
                  justifyContent: 'center',
                  flexWrap: 'wrap',
                }}
              >
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: '0.6875rem', padding: '0.25rem 0.5rem' }}
                  onClick={() => handleDemoFill('alice', 'SecurePass123!')}
                  title="Customer: alice"
                >
                  <UserIcon size={12} /> Alice (Customer)
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: '0.6875rem', padding: '0.25rem 0.5rem' }}
                  onClick={() => handleDemoFill('bob', 'SecurePass123!')}
                  title="Customer: bob"
                >
                  <UserIcon size={12} /> Bob (Customer)
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: '0.6875rem', padding: '0.25rem 0.5rem' }}
                  onClick={() => handleDemoFill('sec_admin', 'AdminSecurePass999!')}
                  title="SecOps Administrator: sec_admin"
                >
                  <Shield size={12} color="var(--color-primary-burgundy)" /> Admin (sec_admin)
                </button>
              </div>
            </div>

            {onNavigateToRegister && (
              <div
                style={{
                  marginTop: '1.25rem',
                  paddingTop: '0.85rem',
                  borderTop: '1px solid var(--color-border)',
                  textAlign: 'center',
                  fontSize: '0.75rem',
                  color: 'var(--color-text-secondary)',
                }}
              >
                <span>Need a demo account? </span>
                <button
                  type="button"
                  onClick={onNavigateToRegister}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--color-primary-burgundy)',
                    fontWeight: 600,
                    cursor: 'pointer',
                    fontSize: '0.75rem',
                    textDecoration: 'underline',
                  }}
                >
                  Create Demo Account
                </button>
              </div>
            )}
          </>
        )}

        {/* STEP 2: MANDATORY OTP VERIFICATION */}
        {step === 'OTP' && (
          <form onSubmit={handleOtpSubmit}>
            {/* Context callout */}
            <div
              style={{
                backgroundColor: 'var(--color-page-bg)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                padding: '0.75rem',
                marginBottom: '1.25rem',
                fontSize: '0.75rem',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '0.25rem',
                }}
              >
                <span style={{ color: 'var(--color-text-secondary)' }}>Authenticating:</span>
                <span style={{ fontWeight: 600, color: 'var(--color-text-main)' }}>
                  {username}
                </span>
              </div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span style={{ color: 'var(--color-text-secondary)' }}>Challenge ID:</span>
                <span className="mono" style={{ fontWeight: 600, color: 'var(--color-text-main)' }}>
                  #{challengeId}
                </span>
              </div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginTop: '0.25rem',
                  paddingTop: '0.25rem',
                  borderTop: '1px solid var(--color-border)',
                }}
              >
                <span style={{ color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                  <Clock size={12} /> Challenge Expiry:
                </span>
                <span
                  className="mono"
                  style={{
                    fontWeight: 600,
                    color: expirySeconds < 60 ? 'var(--color-danger)' : 'var(--color-text-main)',
                  }}
                >
                  {formatTimer(expirySeconds)}
                </span>
              </div>
            </div>

            {/* OTP Input */}
            <div className="form-group">
              <label className="form-label" htmlFor="otp_input">
                Enter 6-Digit One-Time Password
              </label>
              <input
                id="otp_input"
                type="text"
                maxLength={6}
                className="form-input mono"
                placeholder="000000"
                value={otpCode}
                onChange={(e) => {
                  const val = e.target.value.replace(/\D/g, '');
                  setOtpCode(val);
                }}
                style={{
                  fontSize: '1.5rem',
                  letterSpacing: '0.35em',
                  textAlign: 'center',
                  padding: '0.55rem',
                  fontWeight: 600,
                }}
                disabled={loading}
                autoFocus
              />
              <div
                style={{
                  fontSize: '0.6875rem',
                  color: 'var(--color-text-secondary)',
                  marginTop: '0.35rem',
                  textAlign: 'center',
                }}
              >
                Code expires in {formatTimer(expirySeconds)}. Single-use only.
              </div>
            </div>

            {/* Simulated Dev Mailbox Helper (for Local Development & Demo) */}
            {devOtp && (
              <div
                style={{
                  backgroundColor: '#FFFBEB',
                  border: '1px solid #FDE68A',
                  borderRadius: 'var(--radius-md)',
                  padding: '0.5rem 0.75rem',
                  marginBottom: '1rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '0.5rem',
                }}
              >
                <div style={{ fontSize: '0.6875rem', color: '#92400E' }}>
                  <strong>Demo Mailbox:</strong> <span className="mono" style={{ fontWeight: 700 }}>{devOtp}</span>
                </div>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: '0.6875rem', padding: '0.2rem 0.45rem' }}
                  onClick={() => setOtpCode(devOtp)}
                  title="Autofill simulated code"
                >
                  Use Code
                </button>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', padding: '0.55rem' }}
              disabled={loading || otpCode.trim().length !== 6 || expirySeconds <= 0}
            >
              {loading ? (
                <>
                  <RefreshCw size={14} className="spin" /> Verifying OTP Hash...
                </>
              ) : (
                'Verify OTP & Complete Sign In'
              )}
            </button>

            {/* Action Row: Resend & Back */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginTop: '1rem',
                paddingTop: '0.75rem',
                borderTop: '1px solid var(--color-border)',
              }}
            >
              <button
                type="button"
                onClick={handleBackToCredentials}
                className="btn btn-secondary"
                style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}
                disabled={loading}
              >
                <ArrowLeft size={13} /> Back
              </button>

              <button
                type="button"
                onClick={handleResendOtp}
                className="btn btn-secondary"
                style={{
                  fontSize: '0.75rem',
                  padding: '0.3rem 0.6rem',
                  color: cooldownSeconds > 0 ? 'var(--color-text-secondary)' : 'var(--color-primary-burgundy)',
                }}
                disabled={cooldownSeconds > 0 || resending || loading}
              >
                {resending ? (
                  <>
                    <RefreshCw size={12} className="spin" /> Resending...
                  </>
                ) : cooldownSeconds > 0 ? (
                  `Resend in ${cooldownSeconds}s`
                ) : (
                  'Resend Code'
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
