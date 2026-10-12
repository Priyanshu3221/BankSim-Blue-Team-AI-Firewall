import React, { useState } from 'react';
import { ShieldAlert, KeyRound, ScanFace, AlertCircle, CheckCircle2, XCircle, RefreshCw, Lock } from 'lucide-react';
import { api } from '../api/client';

interface VerificationModalProps {
  challengeId: number;
  challengeType: 'OTP' | 'FACE_VERIFICATION';
  explanation?: string;
  onClose: () => void;
  onVerified: (challengeId: number) => void;
}

export const VerificationModal: React.FC<VerificationModalProps> = ({
  challengeId,
  challengeType,
  explanation,
  onClose,
  onVerified,
}) => {
  const [verificationCode, setVerificationCode] = useState('');
  const [faceData, setFaceData] = useState<string>('MOCK_FACE_VALID');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [attemptCount, setAttemptCount] = useState(0);

  const handleVerify = async (codeOverride?: string, faceOverride?: string) => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    const codeToSubmit = codeOverride !== undefined ? codeOverride : verificationCode;
    const faceToSubmit = faceOverride !== undefined ? faceOverride : faceData;

    try {
      const res = await api.verifyChallenge({
        challenge_id: challengeId,
        verification_code: challengeType === 'OTP' ? codeToSubmit.trim() : undefined,
        face_data: challengeType === 'FACE_VERIFICATION' ? faceToSubmit : undefined,
      });

      if (res.status === 'VERIFIED') {
        setSuccess('Challenge verified successfully! Clearance granted.');
        setTimeout(() => {
          onVerified(challengeId);
        }, 1000);
      } else {
        setError(res.message || 'Verification challenge failed.');
      }
    } catch (err: any) {
      setAttemptCount((prev) => prev + 1);
      setError(err.message || 'Verification failed. Please check inputs.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <div style={{
              backgroundColor: challengeType === 'FACE_VERIFICATION' ? 'rgba(84, 44, 56, 0.08)' : '#FFFBEB',
              padding: '0.45rem',
              borderRadius: '4px',
              border: `1px solid ${challengeType === 'FACE_VERIFICATION' ? 'rgba(84, 44, 56, 0.2)' : '#FDE68A'}`,
            }}>
              {challengeType === 'FACE_VERIFICATION' ? (
                <ScanFace size={18} color="var(--color-primary-burgundy)" />
              ) : (
                <KeyRound size={18} color="var(--color-warning)" />
              )}
            </div>
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--color-text-main)' }}>
                {challengeType === 'FACE_VERIFICATION' ? 'Biometric Face Verification' : 'Multi-Factor OTP Clearance'}
              </h3>
              <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-secondary)' }}>
                Challenge ID: <span className="mono" style={{ color: 'var(--color-text-main)', fontWeight: 600 }}>#{challengeId}</span> • 15m Expiry
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn btn-secondary"
            style={{ padding: '0.2rem 0.45rem', fontSize: '0.75rem' }}
            title="Close modal"
          >
            ✕
          </button>
        </div>

        {/* Risk Policy Notice */}
        <div style={{
          backgroundColor: '#FBF9F7',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)',
          padding: '0.625rem 0.75rem',
          marginBottom: '1rem',
          fontSize: '0.75rem',
          color: 'var(--color-text-secondary)',
        }}>
          <div style={{ fontWeight: 600, color: 'var(--color-text-main)', marginBottom: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <ShieldAlert size={14} color="var(--color-warning)" /> Security Policy Triggered
          </div>
          {explanation || 'High risk transaction telemetry requires verified step-up clearance before funds can settle.'}
        </div>

        {/* Success Alert */}
        {success && (
          <div className="alert-box alert-box-success" style={{ marginBottom: '1rem' }}>
            <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
            <span style={{ fontSize: '0.8125rem', fontWeight: 600 }}>{success}</span>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="alert-box alert-box-danger" style={{ marginBottom: '1rem' }}>
            <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <div style={{ fontSize: '0.8125rem', fontWeight: 600 }}>Verification Rejected</div>
              <div style={{ fontSize: '0.75rem', marginTop: '0.2rem' }}>{error}</div>
              {attemptCount > 0 && attemptCount < 3 && (
                <div style={{ fontSize: '0.6875rem', marginTop: '0.2rem', color: 'var(--color-warning)' }}>
                  Failed attempts: {attemptCount} / 3. Challenge locks permanently on 3rd failure.
                </div>
              )}
            </div>
          </div>
        )}

        {/* OTP Input Section */}
        {challengeType === 'OTP' ? (
          <div>
            <div className="form-group">
              <label className="form-label" htmlFor="otp_code">
                Enter 6-Digit One-Time Password
              </label>
              <input
                id="otp_code"
                type="text"
                maxLength={6}
                className="form-input mono"
                placeholder="000000"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value)}
                style={{
                  fontSize: '1.25rem',
                  letterSpacing: '0.4em',
                  textAlign: 'center',
                  padding: '0.5rem',
                }}
                disabled={loading || Boolean(success)}
              />
              <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-secondary)', marginTop: '0.25rem' }}>
                Delivered out-of-band via simulation dev mailbox. Plaintext is never stored in DB.
              </div>
            </div>

            <button
              onClick={() => handleVerify()}
              className="btn btn-primary"
              style={{ width: '100%', padding: '0.55rem' }}
              disabled={loading || !verificationCode.trim() || Boolean(success)}
            >
              {loading ? <><RefreshCw size={14} className="spin" /> Verifying OTP Hash...</> : 'Verify and Authorize Transfer'}
            </button>
          </div>
        ) : (
          /* Face Verification Section */
          <div>
            <div style={{
              backgroundColor: '#FBF9F7',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              padding: '1rem',
              textAlign: 'center',
              marginBottom: '1rem',
            }}>
              <span className="badge badge-burgundy" style={{ marginBottom: '0.5rem', fontSize: '0.625rem' }}>
                SIMULATED BIOMETRIC ENGINE (PHASE 7)
              </span>

              {/* Viewfinder Graphic */}
              <div style={{
                width: '80px',
                height: '80px',
                border: '1px dashed var(--color-primary-burgundy)',
                borderRadius: '50%',
                margin: '0 auto 0.5rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#FFFFFF',
              }}>
                <ScanFace size={40} color="var(--color-primary-burgundy)" />
              </div>

              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-main)', fontWeight: 500 }}>
                Simulated Facial Liveness Inspection
              </div>
              <div style={{ fontSize: '0.6875rem', color: 'var(--color-success)', marginTop: '0.2rem' }}>
                <Lock size={11} style={{ display: 'inline', verticalAlign: '-1px' }} /> Privacy Guarantee: Raw images and embeddings are never stored.
              </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-secondary)', marginBottom: '0.4rem', textTransform: 'uppercase', fontWeight: 600 }}>
                Select Biometric Simulation Response:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                <button
                  type="button"
                  onClick={() => {
                    setFaceData('MOCK_FACE_VALID');
                    handleVerify(undefined, 'MOCK_FACE_VALID');
                  }}
                  className="btn btn-secondary"
                  style={{ justifyContent: 'flex-start', borderColor: 'var(--color-success-border)', fontSize: '0.75rem', padding: '0.4rem 0.6rem' }}
                  disabled={loading || Boolean(success)}
                >
                  <CheckCircle2 size={14} color="var(--color-success)" />
                  <span><strong>Simulate Valid Face Scan</strong> (High Confidence)</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setFaceData('MOCK_FACE_SPOOF');
                    handleVerify(undefined, 'MOCK_FACE_SPOOF');
                  }}
                  className="btn btn-secondary"
                  style={{ justifyContent: 'flex-start', borderColor: 'var(--color-danger-border)', fontSize: '0.75rem', padding: '0.4rem 0.6rem' }}
                  disabled={loading || Boolean(success)}
                >
                  <XCircle size={14} color="var(--color-danger)" />
                  <span><strong>Simulate Liveness Spoof Attack</strong> (Replay)</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setFaceData('MOCK_FACE_MISMATCH');
                    handleVerify(undefined, 'MOCK_FACE_MISMATCH');
                  }}
                  className="btn btn-secondary"
                  style={{ justifyContent: 'flex-start', borderColor: 'var(--color-warning-border)', fontSize: '0.75rem', padding: '0.4rem 0.6rem' }}
                  disabled={loading || Boolean(success)}
                >
                  <AlertCircle size={14} color="var(--color-warning)" />
                  <span><strong>Simulate Unenrolled Face Mismatch</strong></span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
