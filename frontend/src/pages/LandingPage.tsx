import React from 'react';
import {
  ShieldCheck,
  Lock,
  ArrowRight,
  UserPlus,
  LogIn,
  Layers,
  History,
  SendHorizontal,
  Cpu,
  AlertTriangle,
  Fingerprint,
} from 'lucide-react';

interface LandingPageProps {
  onNavigateToLogin: () => void;
  onNavigateToRegister: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onNavigateToLogin,
  onNavigateToRegister,
}) => {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--color-page-bg)' }}>
      {/* 1. Header Navigation Bar */}
      <header
        style={{
          backgroundColor: 'var(--color-surface)',
          borderBottom: '1px solid var(--color-border)',
          position: 'sticky',
          top: 0,
          zIndex: 40,
        }}
      >
        <div
          style={{
            maxWidth: '1200px',
            margin: '0 auto',
            padding: '0.875rem 1.5rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
          }}
        >
          {/* Brand Wordmark */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                backgroundColor: 'var(--color-primary-burgundy)',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#FFFFFF',
              }}
            >
              <ShieldCheck size={20} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.4rem' }}>
                <span style={{ fontSize: '1.1875rem', fontWeight: 700, color: 'var(--color-primary-burgundy)', letterSpacing: '-0.02em' }}>
                  BankSim
                </span>
                <span style={{ fontSize: '0.6875rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Blue-Team AI
                </span>
              </div>
              <p style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', margin: 0 }}>
                Simulated Digital Banking & Security Firewall
              </p>
            </div>
          </div>

          {/* Simple Navigation Links */}
          <nav style={{ display: 'flex', alignItems: 'center', gap: '1.75rem' }}>
            <a
              href="#services"
              style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', textDecoration: 'none', fontWeight: 500 }}
            >
              Banking Services
            </a>
            <a
              href="#security"
              style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', textDecoration: 'none', fontWeight: 500 }}
            >
              AI Firewall
            </a>
            <a
              href="#demo-details"
              style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', textDecoration: 'none', fontWeight: 500 }}
            >
              Demo Platform
            </a>
          </nav>

          {/* Action CTAs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              onClick={onNavigateToLogin}
              style={{
                padding: '0.5rem 1rem',
                fontSize: '0.8125rem',
                fontWeight: 600,
                color: 'var(--color-primary-burgundy)',
                backgroundColor: 'transparent',
                border: '1px solid var(--color-primary-burgundy)',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
              }}
            >
              <LogIn size={14} />
              <span>Sign In</span>
            </button>
            <button
              onClick={onNavigateToRegister}
              style={{
                padding: '0.5rem 1.125rem',
                fontSize: '0.8125rem',
                fontWeight: 600,
                color: '#FFFFFF',
                backgroundColor: 'var(--color-primary-burgundy)',
                border: '1px solid var(--color-primary-burgundy)',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
              }}
            >
              <UserPlus size={14} />
              <span>Create Demo Account</span>
            </button>
          </div>
        </div>
      </header>

      {/* 2. Hero Section: Understated Formal Banking Banner */}
      <section
        style={{
          backgroundColor: '#FFFFFF',
          borderBottom: '1px solid var(--color-border)',
          padding: '3.5rem 1.5rem',
        }}
      >
        <div style={{ maxWidth: '1000px', margin: '0 auto', textAlign: 'center' }}>
          {/* Security Badge */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.3rem 0.85rem',
              backgroundColor: '#F9F6F4',
              border: '1px solid var(--color-border)',
              borderRadius: '999px',
              fontSize: '0.75rem',
              color: 'var(--color-primary-burgundy)',
              fontWeight: 600,
              marginBottom: '1.25rem',
            }}
          >
            <Lock size={12} />
            <span>Interactive Blue-Team AI Defense Demonstration</span>
          </div>

          <h1
            style={{
              fontSize: '2.375rem',
              fontWeight: 700,
              color: 'var(--color-primary-burgundy)',
              lineHeight: 1.25,
              marginBottom: '1rem',
              letterSpacing: '-0.02em',
            }}
          >
            Formal Digital Banking with Adaptive AI Defense
          </h1>

          <p
            style={{
              fontSize: '1rem',
              color: 'var(--color-text-secondary)',
              maxWidth: '720px',
              margin: '0 auto 2rem auto',
              lineHeight: 1.6,
            }}
          >
            BankSim provides a full simulated retail banking experience backed by real-time behavioral risk scoring and LLM threat analysis. Explore account ledgers, simulate peer transfers, and observe defensive step-up verification under hostile conditions.
          </p>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <button
              onClick={onNavigateToRegister}
              style={{
                padding: '0.75rem 1.75rem',
                fontSize: '0.9375rem',
                fontWeight: 600,
                color: '#FFFFFF',
                backgroundColor: 'var(--color-primary-burgundy)',
                border: '1px solid var(--color-primary-burgundy)',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <span>Create Demo Account</span>
              <ArrowRight size={16} />
            </button>

            <button
              onClick={onNavigateToLogin}
              style={{
                padding: '0.75rem 1.75rem',
                fontSize: '0.9375rem',
                fontWeight: 600,
                color: 'var(--color-primary-burgundy)',
                backgroundColor: '#FFFFFF',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <LogIn size={16} />
              <span>Sign In to Demo Portal</span>
            </button>
          </div>

          <div
            style={{
              marginTop: '2rem',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '2rem',
              fontSize: '0.75rem',
              color: 'var(--color-text-muted)',
              borderTop: '1px solid var(--color-border-subtle)',
              paddingTop: '1.25rem',
            }}
          >
            <span>✓ Pre-seeded ₹50,000 Sandbox Balance</span>
            <span>✓ Mandatory OTP Sign-in Protection</span>
            <span>✓ Real-time AI Risk Evaluation</span>
          </div>
        </div>
      </section>

      {/* 3. Banking Services Section */}
      <section id="services" style={{ padding: '3.5rem 1.5rem', maxWidth: '1100px', margin: '0 auto', width: '100%' }}>
        <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-text-main)', marginBottom: '0.5rem' }}>
            Simulated Retail Banking Services
          </h2>
          <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)', maxWidth: '600px', margin: '0 auto' }}>
            Every demo account receives an isolated ledger profile with comprehensive banking operations.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
          {/* Service 1 */}
          <div
            style={{
              backgroundColor: '#FFFFFF',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              padding: '1.75rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}
          >
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: '#F7F3F0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-primary-burgundy)',
              }}
            >
              <Layers size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: 'var(--color-text-main)', marginBottom: '0.4rem' }}>
                Account Balance & Limits
              </h3>
              <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Authoritative server-side balance derivation. Each new registration automatically receives ₹50,000 in simulated demo funds for test transactions.
              </p>
            </div>
          </div>

          {/* Service 2 */}
          <div
            style={{
              backgroundColor: '#FFFFFF',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              padding: '1.75rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}
          >
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: '#F7F3F0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-primary-burgundy)',
              }}
            >
              <History size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: 'var(--color-text-main)', marginBottom: '0.4rem' }}>
                Complete Transaction Ledger
              </h3>
              <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Comprehensive historical statement with debit/credit categorization, counterparty resolution, search filters, and strict user ownership boundaries.
              </p>
            </div>
          </div>

          {/* Service 3 */}
          <div
            style={{
              backgroundColor: '#FFFFFF',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              padding: '1.75rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}
          >
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: '#F7F3F0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-primary-burgundy)',
              }}
            >
              <SendHorizontal size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: 'var(--color-text-main)', marginBottom: '0.4rem' }}>
                Simulated Fund Transfers
              </h3>
              <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Instant peer-to-peer transfers between demo accounts with recipient validation, balance checks, and atomic database consistency.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Security Architecture & AI Firewall Section */}
      <section
        id="security"
        style={{
          backgroundColor: '#FFFFFF',
          borderTop: '1px solid var(--color-border)',
          borderBottom: '1px solid var(--color-border)',
          padding: '3.5rem 1.5rem',
        }}
      >
        <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-text-main)', marginBottom: '0.5rem' }}>
              Defensive AI Security Architecture
            </h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)', maxWidth: '650px', margin: '0 auto' }}>
              BankSim pairs deterministic transaction safeguards with real-time heuristic and generative threat analysis.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
            {/* Feature A: Mandatory Login OTP */}
            <div
              style={{
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                padding: '1.5rem',
                backgroundColor: '#FAFAF8',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                <div
                  style={{
                    padding: '0.4rem',
                    backgroundColor: 'var(--color-primary-burgundy)',
                    borderRadius: 'var(--radius-sm)',
                    color: '#FFFFFF',
                  }}
                >
                  <Lock size={16} />
                </div>
                <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--color-text-main)', margin: 0 }}>
                  Mandatory Login OTP
                </h4>
              </div>
              <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Every login session requires a 6-digit one-time password verification. Codes are salted and cryptographically hashed before storage, bound to short-lived sessions, and protected against replay and brute-force attacks.
              </p>
            </div>

            {/* Feature B: Adaptive Risk Engine */}
            <div
              style={{
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                padding: '1.5rem',
                backgroundColor: '#FAFAF8',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                <div
                  style={{
                    padding: '0.4rem',
                    backgroundColor: 'var(--color-primary-burgundy)',
                    borderRadius: 'var(--radius-sm)',
                    color: '#FFFFFF',
                  }}
                >
                  <Cpu size={16} />
                </div>
                <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--color-text-main)', margin: 0 }}>
                  Adaptive Risk Scoring
                </h4>
              </div>
              <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Every transfer evaluates 5 multi-dimensional signals: transaction velocity bursts, extreme amount deviations, recipient novelty, recent failed attempts, and LLM memo threat classification.
              </p>
            </div>

            {/* Feature C: Step-Up Verification */}
            <div
              style={{
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                padding: '1.5rem',
                backgroundColor: '#FAFAF8',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                <div
                  style={{
                    padding: '0.4rem',
                    backgroundColor: 'var(--color-primary-burgundy)',
                    borderRadius: 'var(--radius-sm)',
                    color: '#FFFFFF',
                  }}
                >
                  <Fingerprint size={16} />
                </div>
                <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--color-text-main)', margin: 0 }}>
                  Risk-Based Step-Up Challenges
                </h4>
              </div>
              <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                High-value transfers (such as Judge B's ₹25,00,000 demonstration) automatically trigger a step-up challenge. The transaction remains restricted until verified through an authenticated one-time challenge.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Demo Platform Credentials & Testing Guide */}
      <section id="demo-details" style={{ padding: '3.5rem 1.5rem', maxWidth: '1100px', margin: '0 auto', width: '100%' }}>
        <div
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            padding: '2rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <AlertTriangle size={20} color="var(--color-warning)" />
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--color-text-main)', margin: 0 }}>
              Judges & Evaluators Quick Demonstration Guide
            </h3>
          </div>
          <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', lineHeight: 1.5, marginBottom: '1.5rem' }}>
            You can create your own custom demo account using the <strong>Create Demo Account</strong> form, or immediately evaluate using the pre-configured demonstration personas:
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '1rem', backgroundColor: '#FAFAF8' }}>
              <strong style={{ fontSize: '0.875rem', color: 'var(--color-primary-burgundy)' }}>Judge A — Normal Activity</strong>
              <p style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', margin: '0.35rem 0' }}>
                Account: <code>alice</code> (₹1,00,000 balance). Executes small transfers (e.g. ₹500), views ledger history, and receives low-risk clearance.
              </p>
            </div>

            <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '1rem', backgroundColor: '#FAFAF8' }}>
              <strong style={{ fontSize: '0.875rem', color: 'var(--color-primary-burgundy)' }}>Judge B — High-Risk Step-Up</strong>
              <p style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', margin: '0.35rem 0' }}>
                Account: <code>bob</code> (₹50,00,000 balance). Initiates a ₹25,00,000 transfer to trigger the adaptive risk firewall's step-up verification.
              </p>
            </div>

            <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '1rem', backgroundColor: '#FAFAF8' }}>
              <strong style={{ fontSize: '0.875rem', color: 'var(--color-primary-burgundy)' }}>Security Administrator</strong>
              <p style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', margin: '0.35rem 0' }}>
                Account: <code>sec_admin</code>. Inspects real-time security events, blocked threat logs, and system metrics.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Regulatory Disclaimer & Footer */}
      <footer
        style={{
          backgroundColor: '#FFFFFF',
          borderTop: '1px solid var(--color-border)',
          marginTop: 'auto',
          padding: '2.5rem 1.5rem',
        }}
      >
        <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
          {/* Prominent Demo Disclosure */}
          <div
            style={{
              padding: '1rem 1.25rem',
              backgroundColor: '#FBF9F7',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-sm)',
              marginBottom: '2rem',
              fontSize: '0.75rem',
              color: 'var(--color-text-secondary)',
              lineHeight: 1.6,
            }}
          >
            <strong style={{ color: 'var(--color-text-main)' }}>Demonstration Platform Disclosure:</strong> BankSim is an educational and cybersecurity research demonstration platform developed to showcase blue-team AI defense engineering. BankSim is not a licensed financial institution, does not hold banking deposits, and does not connect to real payment settlement networks. All balances, account numbers, and transactions are strictly simulated demo entities.
          </div>

          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '1rem',
              fontSize: '0.75rem',
              color: 'var(--color-text-muted)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShieldCheck size={16} color="var(--color-primary-burgundy)" />
              <span style={{ fontWeight: 600, color: 'var(--color-text-main)' }}>BankSim — Blue-Team AI Firewall</span>
              <span>© 2026 Simulated Banking Demo</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
              <button
                onClick={onNavigateToLogin}
                style={{ background: 'none', border: 'none', color: 'var(--color-primary-burgundy)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}
              >
                Sign In
              </button>
              <button
                onClick={onNavigateToRegister}
                style={{ background: 'none', border: 'none', color: 'var(--color-primary-burgundy)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}
              >
                Create Account
              </button>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};
