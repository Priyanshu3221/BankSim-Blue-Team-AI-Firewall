import React, { useEffect, useState } from 'react';
import { ShieldAlert, Users, CreditCard, ArrowRightLeft, Activity, RefreshCw, AlertCircle, Filter, Lock } from 'lucide-react';
import { api, ApiError } from '../api/client';
import { SeverityBadge } from '../components/Badge';
import { useAuth } from '../context/AuthContext';
import type { AdminDashboardMetrics, SecurityEventItem } from '../api/types';

export const AdminPage: React.FC = () => {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<AdminDashboardMetrics | null>(null);
  const [events, setEvents] = useState<SecurityEventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');

  const loadAdminData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashMetrics, secEvents] = await Promise.all([
        api.getAdminDashboard(),
        api.getAdminSecurityEvents(50),
      ]);
      setMetrics(dashMetrics);
      setEvents(secEvents);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 403) {
        setError('403 Forbidden: Administrator authorization required. Backend RBAC denied access.');
      } else {
        setError(err.message || 'Failed to load administrator telemetry.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  // If user is not ADMIN, show strict RBAC boundary banner
  if (user?.role !== 'ADMIN') {
    return (
      <div style={{ maxWidth: '560px', margin: '3.5rem auto', textAlign: 'center' }}>
        <div className="card" style={{ padding: '2rem 1.5rem' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '4px',
            backgroundColor: 'var(--color-danger-bg)',
            margin: '0 auto 1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Lock size={20} color="var(--color-danger)" />
          </div>
          <h2 style={{ fontSize: '1.125rem', color: 'var(--color-text-main)', marginBottom: '0.35rem', fontWeight: 600 }}>
            Restricted Administrator Console
          </h2>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.8125rem', marginBottom: '1rem', lineHeight: 1.5 }}>
            Account <strong style={{ color: 'var(--color-text-main)' }}>{user?.username}</strong> holds role{' '}
            <span className="badge badge-neutral">{user?.role}</span>. Administrator telemetry and security audit logs are restricted strictly to <strong style={{ color: 'var(--color-danger)' }}>ADMIN</strong> role.
          </p>
          <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-secondary)' }}>
            Backend route <span className="mono">/api/v1/admin/*</span> enforces database authorization.
          </div>
        </div>
      </div>
    );
  }

  const filteredEvents = events.filter((ev) => {
    if (severityFilter === 'ALL') return true;
    return ev.severity === severityFilter;
  });

  return (
    <div>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.75rem',
        marginBottom: '1.25rem',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.15rem' }}>
            <h1 style={{ fontSize: '1.375rem', fontWeight: 600, color: 'var(--color-text-main)' }}>
              SecOps Administrator Console
            </h1>
            <span className="badge badge-danger">ADMIN ONLY</span>
          </div>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.8125rem' }}>
            Real-time audit log events, firewall enforcement, and system telemetry from SQLite.
          </p>
        </div>

        <button onClick={loadAdminData} className="btn btn-secondary" disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh Telemetry
        </button>
      </div>

      {error && (
        <div className="alert-box alert-box-danger" style={{ marginBottom: '1rem' }}>
          <AlertCircle size={16} style={{ flexShrink: 0 }} />
          <div>{error}</div>
        </div>
      )}

      {/* Metric Cards */}
      {metrics && (
        <div className="grid-4" style={{ marginBottom: '1.25rem' }}>
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-text-secondary)', fontSize: '0.6875rem', fontWeight: 600 }}>
              <span>REGISTERED USERS</span>
              <Users size={14} color="var(--color-primary-burgundy)" />
            </div>
            <div style={{ fontSize: '1.375rem', fontWeight: 700, marginTop: '0.25rem', color: 'var(--color-text-main)' }}>
              {metrics.total_users}
            </div>
          </div>

          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-text-secondary)', fontSize: '0.6875rem', fontWeight: 600 }}>
              <span>BANKING ACCOUNTS</span>
              <CreditCard size={14} color="var(--color-primary-burgundy)" />
            </div>
            <div style={{ fontSize: '1.375rem', fontWeight: 700, marginTop: '0.25rem', color: 'var(--color-text-main)' }}>
              {metrics.total_accounts}
            </div>
          </div>

          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-text-secondary)', fontSize: '0.6875rem', fontWeight: 600 }}>
              <span>TOTAL TRANSACTIONS</span>
              <ArrowRightLeft size={14} color="var(--color-primary-burgundy)" />
            </div>
            <div style={{ fontSize: '1.375rem', fontWeight: 700, marginTop: '0.25rem', color: 'var(--color-text-main)' }}>
              {metrics.total_transactions}
            </div>
          </div>

          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-text-secondary)', fontSize: '0.6875rem', fontWeight: 600 }}>
              <span>SECURITY EVENTS (24H)</span>
              <Activity size={14} color="var(--color-danger)" />
            </div>
            <div style={{ fontSize: '1.375rem', fontWeight: 700, marginTop: '0.25rem', color: 'var(--color-danger)' }}>
              {metrics.security_events_24h}
            </div>
            <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-secondary)', marginTop: '0.1rem' }}>
              {metrics.high_risk_events_24h} high/critical risk events
            </div>
          </div>
        </div>
      )}

      {/* Security Events Audit Table */}
      <div className="card">
        <div className="card-header" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
          <div className="card-title">
            <ShieldAlert size={16} color="var(--color-danger)" /> Security Audit Event Log
          </div>

          {/* Severity Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <Filter size={13} color="var(--color-text-secondary)" />
            <span style={{ fontSize: '0.6875rem', color: 'var(--color-text-secondary)', marginRight: '0.2rem' }}>Filter:</span>
            {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
              <button
                key={sev}
                type="button"
                onClick={() => setSeverityFilter(sev)}
                className={`btn ${severityFilter === sev ? 'btn-primary' : 'btn-secondary'}`}
                style={{ fontSize: '0.625rem', padding: '0.2rem 0.4rem' }}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--color-text-secondary)' }}>
            <RefreshCw size={20} className="spin" style={{ margin: '0 auto 0.4rem' }} />
            <div>Loading security audit events...</div>
          </div>
        ) : filteredEvents.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--color-text-secondary)' }}>
            No security events found matching current filter.
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Timestamp</th>
                  <th>Event Type</th>
                  <th>Severity</th>
                  <th>Risk Score</th>
                  <th>User ID</th>
                  <th>Audit Description</th>
                </tr>
              </thead>
              <tbody>
                {filteredEvents.map((ev) => (
                  <tr key={ev.id}>
                    <td className="mono" style={{ color: 'var(--color-text-main)', fontWeight: 600 }}>#{ev.id}</td>
                    <td style={{ fontSize: '0.6875rem', color: 'var(--color-text-secondary)', whiteSpace: 'nowrap' }}>
                      {new Date(ev.created_at).toLocaleString()}
                    </td>
                    <td>
                      <span className="badge badge-neutral mono" style={{ fontSize: '0.625rem' }}>
                        {ev.event_type}
                      </span>
                    </td>
                    <td>
                      <SeverityBadge severity={ev.severity} />
                    </td>
                    <td className="mono" style={{ fontSize: '0.75rem' }}>
                      {ev.risk_score !== null && ev.risk_score !== undefined ? `${ev.risk_score}/100` : '—'}
                    </td>
                    <td className="mono" style={{ fontSize: '0.75rem' }}>
                      {ev.user_id ? `#${ev.user_id}` : 'Unauthenticated'}
                    </td>
                    <td style={{ fontSize: '0.75rem', color: 'var(--color-text-main)', maxWidth: '420px' }}>
                      {ev.description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
