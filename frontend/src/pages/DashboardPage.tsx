import React, { useEffect, useState } from 'react';
import {
  Landmark,
  ArrowRightLeft,
  ShieldCheck,
  Activity,
  AlertCircle,
  RefreshCw,
  CreditCard,
  Shield,
  Eye,
  EyeOff,
  History,
  ArrowUpRight,
  ArrowDownLeft,
  CheckCircle2,
  Clock,
  XCircle,
  ArrowRight,
} from 'lucide-react';
import { api } from '../api/client';
import type { Account, CustomerTransactionItem, User } from '../api/types';

interface DashboardPageProps {
  onNavigate: (page: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [profile, setProfile] = useState<User | null>(null);
  const [recentTransactions, setRecentTransactions] = useState<CustomerTransactionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showMaskedAccount, setShowMaskedAccount] = useState<Record<number, boolean>>({});

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [accs, usr, txRes] = await Promise.all([
        api.getAccounts(),
        api.getCurrentUser(),
        api.getTransactions({ limit: 5 }),
      ]);
      setAccounts(accs);
      setProfile(usr);
      setRecentTransactions(txRes.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load banking dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const formatINR = (paise: number) => {
    const inr = paise / 100;
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(inr);
  };

  const getMaskedAccountNumber = (accNumber: string, isRevealed: boolean) => {
    if (isRevealed || accNumber.length < 5) return accNumber;
    const prefix = accNumber.slice(0, 3);
    const suffix = accNumber.slice(-2);
    return `${prefix}•••${suffix}`;
  };

  const toggleMask = (accId: number) => {
    setShowMaskedAccount((prev) => ({
      ...prev,
      [accId]: !prev[accId],
    }));
  };

  const totalBalancePaise = accounts.reduce((acc, a) => acc + a.balance, 0);

  return (
    <div>
      {/* Top Welcome & Actions Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
          marginBottom: '1.25rem',
        }}
      >
        <div>
          <h1 style={{ fontSize: '1.375rem', fontWeight: 600, color: 'var(--color-text-main)', marginBottom: '0.15rem' }}>
            Account Overview
          </h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.8125rem' }}>
            Customer: <strong style={{ color: 'var(--color-text-main)' }}>{profile?.username || 'Customer'}</strong> • Account #{profile?.id}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button onClick={loadData} className="btn btn-secondary" disabled={loading} title="Refresh accounts">
            <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
          </button>
          <button onClick={() => onNavigate('transfer')} className="btn btn-primary">
            <ArrowRightLeft size={14} /> New Transfer
          </button>
        </div>
      </div>

      {error && (
        <div className="alert-box alert-box-danger" style={{ marginBottom: '1rem' }}>
          <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>{error}</div>
        </div>
      )}

      {/* Primary Metrics: Balances & Defense Overview */}
      <div className="grid-3" style={{ marginBottom: '1.25rem' }}>
        {/* Total Balance Card */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
              Total Liquid Holdings
            </span>
            <Landmark size={16} color="var(--color-primary-burgundy)" />
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-text-main)', lineHeight: 1.2 }}>
            {formatINR(totalBalancePaise)}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginTop: '0.25rem' }}>
            Across {accounts.length} active {accounts.length === 1 ? 'account' : 'accounts'}
          </div>
        </div>

        {/* AI Firewall State Card */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
              Firewall Protection
            </span>
            <ShieldCheck size={16} color="var(--color-success)" />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--color-text-main)' }}>Active Defense</span>
            <span className="badge badge-safe">Online</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginTop: '0.25rem' }}>
            Dual-Engine: Adaptive Risk + AI Threat Inspection
          </div>
        </div>

        {/* Security Policy Card */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
              Security Policy
            </span>
            <Shield size={16} color="var(--color-primary-burgundy)" />
          </div>
          <div style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--color-text-main)' }}>
            Fail-Closed
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginTop: '0.25rem' }}>
            Step-up challenge required on anomaly detection
          </div>
        </div>
      </div>

      {/* Account Listings with Masking Option */}
      <div className="card" style={{ marginBottom: '1.25rem' }}>
        <div className="card-header">
          <div className="card-title">
            <CreditCard size={16} color="var(--color-primary-burgundy)" /> Banking Accounts
          </div>
          <span className="badge badge-neutral">{accounts.length} Registered</span>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--color-text-secondary)' }}>
            <RefreshCw size={20} className="spin" style={{ margin: '0 auto 0.5rem' }} />
            <div>Loading accounts...</div>
          </div>
        ) : accounts.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--color-text-secondary)' }}>
            No active banking accounts linked to this user.
          </div>
        ) : (
          <div className="grid-2">
            {accounts.map((acc) => {
              const isRevealed = !!showMaskedAccount[acc.id];
              return (
                <div
                  key={acc.id}
                  style={{
                    backgroundColor: '#FFFFFF',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                    padding: '1rem',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <span className="badge badge-neutral">
                        {acc.account_type} ACCOUNT
                      </span>
                      <span className="badge badge-safe">ACTIVE</span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                      <span className="mono" style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--color-text-main)' }}>
                        {getMaskedAccountNumber(acc.account_number, isRevealed)}
                      </span>
                      <button
                        type="button"
                        onClick={() => toggleMask(acc.id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          color: 'var(--color-text-secondary)',
                          padding: '2px',
                          display: 'flex',
                          alignItems: 'center',
                        }}
                        title={isRevealed ? 'Mask account number' : 'Show full account number'}
                      >
                        {isRevealed ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                    </div>

                    <div style={{ marginBottom: '1rem' }}>
                      <div style={{ fontSize: '0.6875rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                        Available Balance
                      </div>
                      <div style={{ fontSize: '1.375rem', fontWeight: 700, color: 'var(--color-text-main)' }}>
                        {formatINR(acc.balance)}
                      </div>
                      <div className="mono" style={{ fontSize: '0.6875rem', color: 'var(--color-text-secondary)' }}>
                        {acc.balance.toLocaleString()} paise ({acc.currency})
                      </div>
                    </div>
                  </div>

                  <div style={{
                    paddingTop: '0.75rem',
                    borderTop: '1px solid var(--color-border-subtle)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}>
                    <span style={{ fontSize: '0.6875rem', color: 'var(--color-text-secondary)' }}>
                      Opened: {new Date(acc.created_at).toLocaleDateString()}
                    </span>
                    <button
                      onClick={() => onNavigate('transfer')}
                      className="btn btn-secondary"
                      style={{ fontSize: '0.6875rem', padding: '0.25rem 0.55rem' }}
                    >
                      Transfer <ArrowRightLeft size={12} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Recent Activity Card */}
      <div className="card" style={{ marginBottom: '1.25rem', padding: 0, overflow: 'hidden' }}>
        <div
          style={{
            padding: '0.875rem 1.25rem',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            backgroundColor: '#FAFAF8',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <History size={16} color="var(--color-primary-burgundy)" />
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--color-text-main)' }}>
              Recent Account Activity
            </span>
          </div>
          <button
            onClick={() => onNavigate('transactions')}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--color-primary-burgundy)',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
            }}
          >
            <span>View Full Statement</span>
            <ArrowRight size={12} />
          </button>
        </div>

        {recentTransactions.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-secondary)', fontSize: '0.8125rem' }}>
            No recent activity recorded for this account.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
              <thead>
                <tr style={{ backgroundColor: '#FDFBF9', borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{ padding: '0.6rem 1rem', fontWeight: 600, color: 'var(--color-text-secondary)', fontSize: '0.71875rem' }}>
                    DATE
                  </th>
                  <th style={{ padding: '0.6rem 1rem', fontWeight: 600, color: 'var(--color-text-secondary)', fontSize: '0.71875rem' }}>
                    DESCRIPTION
                  </th>
                  <th style={{ padding: '0.6rem 1rem', fontWeight: 600, color: 'var(--color-text-secondary)', fontSize: '0.71875rem' }}>
                    TYPE
                  </th>
                  <th style={{ padding: '0.6rem 1rem', fontWeight: 600, color: 'var(--color-text-secondary)', fontSize: '0.71875rem', textAlign: 'right' }}>
                    AMOUNT
                  </th>
                  <th style={{ padding: '0.6rem 1rem', fontWeight: 600, color: 'var(--color-text-secondary)', fontSize: '0.71875rem', textAlign: 'center' }}>
                    STATUS
                  </th>
                </tr>
              </thead>
              <tbody>
                {recentTransactions.map((tx) => {
                  const isDebit = tx.direction === 'DEBIT';
                  return (
                    <tr
                      key={tx.id}
                      style={{ borderBottom: '1px solid var(--color-border-subtle)' }}
                    >
                      <td style={{ padding: '0.65rem 1rem', whiteSpace: 'nowrap', color: 'var(--color-text-secondary)' }}>
                        {new Date(tx.created_at).toLocaleDateString()}
                      </td>
                      <td style={{ padding: '0.65rem 1rem' }}>
                        <div style={{ fontWeight: 500, color: 'var(--color-text-main)' }}>{tx.description}</div>
                        <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)' }}>
                          Ref: <span className="mono">{tx.transaction_reference}</span>
                        </div>
                      </td>
                      <td style={{ padding: '0.65rem 1rem', whiteSpace: 'nowrap' }}>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            fontSize: '0.6875rem',
                            fontWeight: 600,
                            padding: '0.15rem 0.45rem',
                            borderRadius: '3px',
                            backgroundColor: isDebit ? 'var(--color-danger-bg)' : 'var(--color-success-bg)',
                            color: isDebit ? 'var(--color-danger)' : 'var(--color-success)',
                            border: `1px solid ${isDebit ? 'var(--color-danger-border)' : 'var(--color-success-border)'}`,
                          }}
                        >
                          {isDebit ? <ArrowUpRight size={11} /> : <ArrowDownLeft size={11} />}
                          <span>{isDebit ? 'DEBIT' : 'CREDIT'}</span>
                        </span>
                      </td>
                      <td style={{ padding: '0.65rem 1rem', textAlign: 'right', whiteSpace: 'nowrap', fontWeight: 600 }}>
                        <span style={{ color: isDebit ? 'var(--color-text-main)' : 'var(--color-success)' }}>
                          {isDebit ? '- ' : '+ '}{formatINR(tx.amount_paise)}
                        </span>
                      </td>
                      <td style={{ padding: '0.65rem 1rem', textAlign: 'center', whiteSpace: 'nowrap' }}>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            fontSize: '0.6875rem',
                            fontWeight: 600,
                            padding: '0.15rem 0.45rem',
                            borderRadius: '3px',
                            backgroundColor:
                              tx.status === 'COMPLETED'
                                ? 'var(--color-success-bg)'
                                : tx.status === 'PENDING'
                                ? 'var(--color-warning-bg)'
                                : 'var(--color-danger-bg)',
                            color:
                              tx.status === 'COMPLETED'
                                ? 'var(--color-success)'
                                : tx.status === 'PENDING'
                                ? 'var(--color-warning)'
                                : 'var(--color-danger)',
                          }}
                        >
                          {tx.status === 'COMPLETED' ? (
                            <CheckCircle2 size={11} />
                          ) : tx.status === 'PENDING' ? (
                            <Clock size={11} />
                          ) : (
                            <XCircle size={11} />
                          )}
                          <span>{tx.status}</span>
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Security Console Callout Card */}
      <div className="card" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem',
        padding: '1.25rem',
      }}>
        <div style={{ maxWidth: '640px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.25rem' }}>
            <Activity size={16} color="var(--color-primary-burgundy)" />
            <span style={{ fontWeight: 600, fontSize: '0.9375rem', color: 'var(--color-text-main)' }}>
              AI Threat Firewall Diagnostics
            </span>
          </div>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.8125rem' }}>
            Simulate and inspect transaction memos against adversarial prompt injections, jailbreaks, and test the Adaptive Risk Engine.
          </p>
        </div>
        <button onClick={() => onNavigate('security')} className="btn btn-secondary">
          Open Security Console <ShieldCheck size={14} />
        </button>
      </div>
    </div>
  );
};
