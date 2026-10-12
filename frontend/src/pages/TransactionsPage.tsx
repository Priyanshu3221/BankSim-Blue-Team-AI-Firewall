import React, { useEffect, useState, useCallback } from 'react';
import {
  History,
  Search,
  Filter,
  ArrowDownLeft,
  ArrowUpRight,
  RefreshCw,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  Clock,
  XCircle,
  FileText,
  Landmark,
} from 'lucide-react';
import { api } from '../api/client';
import type { CustomerTransactionItem } from '../api/types';

interface TransactionsPageProps {
  onNavigate?: (page: string) => void;
}

export const TransactionsPage: React.FC<TransactionsPageProps> = ({ onNavigate }) => {
  const [transactions, setTransactions] = useState<CustomerTransactionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Pagination
  const [directionFilter, setDirectionFilter] = useState<'ALL' | 'DEBIT' | 'CREDIT'>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(0);
  const pageSize = 10;

  const loadTransactions = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.getTransactions({
        type: directionFilter !== 'ALL' ? directionFilter : undefined,
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
        search: searchQuery.trim() || undefined,
        limit: pageSize,
        offset: page * pageSize,
      });

      setTransactions(response.items);
      setTotal(response.total);
    } catch (err: any) {
      setError(err.message || 'Failed to load transaction ledger statement.');
    } finally {
      setLoading(false);
    }
  }, [directionFilter, statusFilter, searchQuery, page]);

  useEffect(() => {
    loadTransactions();
  }, [loadTransactions]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    loadTransactions();
  };

  const handleResetFilters = () => {
    setDirectionFilter('ALL');
    setStatusFilter('ALL');
    setSearchQuery('');
    setPage(0);
  };

  const formatINR = (paise: number) => {
    const inr = paise / 100;
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(inr);
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div>
      {/* Header */}
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
            Account Statement & Ledger
          </h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.8125rem' }}>
            Authoritative chronological statement of all simulated banking transactions
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button
            onClick={loadTransactions}
            className="btn btn-secondary"
            disabled={loading}
            title="Refresh transactions"
          >
            <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
          </button>
          {onNavigate && (
            <button onClick={() => onNavigate('transfer')} className="btn btn-primary">
              <Landmark size={14} /> New Transfer
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="alert-box alert-box-danger" style={{ marginBottom: '1rem' }}>
          <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>{error}</div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="card" style={{ marginBottom: '1.25rem', padding: '1rem' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center' }}>
          {/* Search Box */}
          <div style={{ flex: '1 1 240px', position: 'relative' }}>
            <Search
              size={15}
              color="var(--color-text-secondary)"
              style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }}
            />
            <input
              type="text"
              placeholder="Search reference, counterparty, or memo..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '0.45rem 0.75rem 0.45rem 2.2rem',
                fontSize: '0.8125rem',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm)',
                outline: 'none',
              }}
            />
          </div>

          {/* Direction Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', fontWeight: 500 }}>Type:</span>
            <select
              value={directionFilter}
              onChange={(e) => {
                setDirectionFilter(e.target.value as any);
                setPage(0);
              }}
              style={{
                padding: '0.45rem 0.65rem',
                fontSize: '0.8125rem',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: '#FFFFFF',
                outline: 'none',
              }}
            >
              <option value="ALL">All Flows</option>
              <option value="DEBIT">Debit (Sent)</option>
              <option value="CREDIT">Credit (Received)</option>
            </select>
          </div>

          {/* Status Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', fontWeight: 500 }}>Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(0);
              }}
              style={{
                padding: '0.45rem 0.65rem',
                fontSize: '0.8125rem',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: '#FFFFFF',
                outline: 'none',
              }}
            >
              <option value="ALL">All Statuses</option>
              <option value="COMPLETED">Completed</option>
              <option value="PENDING">Pending</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>

          {/* Search Button */}
          <button type="submit" className="btn btn-secondary" style={{ padding: '0.45rem 0.85rem' }}>
            <Filter size={14} /> Filter
          </button>

          {(searchQuery || directionFilter !== 'ALL' || statusFilter !== 'ALL') && (
            <button
              type="button"
              onClick={handleResetFilters}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--color-primary-burgundy)',
                fontSize: '0.75rem',
                cursor: 'pointer',
                textDecoration: 'underline',
              }}
            >
              Reset Filters
            </button>
          )}
        </form>
      </div>

      {/* Transactions Table Card */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
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
              Transaction Ledger Records
            </span>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
            Showing {transactions.length} of {total} records
          </span>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '3.5rem', color: 'var(--color-text-secondary)' }}>
            <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.75rem' }} />
            <div style={{ fontSize: '0.875rem' }}>Loading verified ledger statement...</div>
          </div>
        ) : transactions.length === 0 ? (
          /* Informative Empty State */
          <div style={{ textAlign: 'center', padding: '3.5rem 1.5rem', color: 'var(--color-text-secondary)' }}>
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                backgroundColor: '#F5F0EC',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1rem auto',
                color: 'var(--color-primary-burgundy)',
              }}
            >
              <FileText size={24} />
            </div>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--color-text-main)', marginBottom: '0.4rem' }}>
              No Transactions Recorded
            </h3>
            <p style={{ fontSize: '0.8125rem', maxWidth: '440px', margin: '0 auto 1.25rem auto', lineHeight: 1.5 }}>
              No transactions match your current search and filter settings. Newly registered demo accounts will display their initial sandbox credit and subsequent peer transfers here.
            </p>
            {onNavigate && (
              <button onClick={() => onNavigate('transfer')} className="btn btn-primary" style={{ display: 'inline-flex' }}>
                Initiate Simulated Transfer
              </button>
            )}
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
              <thead>
                <tr style={{ backgroundColor: '#FDFBF9', borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--color-text-secondary)', fontSize: '0.71875rem', textTransform: 'uppercase' }}>
                    Date & Time
                  </th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--color-text-secondary)', fontSize: '0.71875rem', textTransform: 'uppercase' }}>
                    Reference #
                  </th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--color-text-secondary)', fontSize: '0.71875rem', textTransform: 'uppercase' }}>
                    Description / Counterparty
                  </th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--color-text-secondary)', fontSize: '0.71875rem', textTransform: 'uppercase' }}>
                    Type
                  </th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--color-text-secondary)', fontSize: '0.71875rem', textTransform: 'uppercase', textAlign: 'right' }}>
                    Amount
                  </th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--color-text-secondary)', fontSize: '0.71875rem', textTransform: 'uppercase', textAlign: 'center' }}>
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => {
                  const isDebit = tx.direction === 'DEBIT';
                  return (
                    <tr
                      key={tx.id}
                      style={{
                        borderBottom: '1px solid var(--color-border-subtle)',
                        transition: 'background-color 0.1s ease',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#FAF7F5')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      {/* Date & Time */}
                      <td style={{ padding: '0.75rem 1rem', whiteSpace: 'nowrap', color: 'var(--color-text-secondary)' }}>
                        <div>{new Date(tx.created_at).toLocaleDateString()}</div>
                        <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)' }}>
                          {new Date(tx.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </td>

                      {/* Reference # */}
                      <td style={{ padding: '0.75rem 1rem', whiteSpace: 'nowrap' }}>
                        <span
                          className="mono"
                          style={{
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            color: 'var(--color-text-main)',
                            backgroundColor: '#F7F3F0',
                            padding: '0.2rem 0.4rem',
                            borderRadius: '3px',
                          }}
                        >
                          {tx.transaction_reference}
                        </span>
                      </td>

                      {/* Description / Memo / Counterparty */}
                      <td style={{ padding: '0.75rem 1rem', maxWidth: '320px' }}>
                        <div style={{ fontWeight: 500, color: 'var(--color-text-main)' }}>
                          {tx.description}
                        </div>
                        {tx.counterparty_account && (
                          <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-secondary)' }}>
                            Counterparty Account: <span className="mono">{tx.counterparty_account}</span>
                          </div>
                        )}
                      </td>

                      {/* Direction Badge */}
                      <td style={{ padding: '0.75rem 1rem', whiteSpace: 'nowrap' }}>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.3rem',
                            fontSize: '0.6875rem',
                            fontWeight: 600,
                            padding: '0.2rem 0.5rem',
                            borderRadius: '3px',
                            backgroundColor: isDebit ? 'var(--color-danger-bg)' : 'var(--color-success-bg)',
                            color: isDebit ? 'var(--color-danger)' : 'var(--color-success)',
                            border: `1px solid ${isDebit ? 'var(--color-danger-border)' : 'var(--color-success-border)'}`,
                          }}
                        >
                          {isDebit ? <ArrowUpRight size={12} /> : <ArrowDownLeft size={12} />}
                          <span>{isDebit ? 'DEBIT' : 'CREDIT'}</span>
                        </span>
                      </td>

                      {/* Amount */}
                      <td style={{ padding: '0.75rem 1rem', textAlign: 'right', whiteSpace: 'nowrap' }}>
                        <div
                          style={{
                            fontWeight: 700,
                            fontSize: '0.875rem',
                            color: isDebit ? 'var(--color-text-main)' : 'var(--color-success)',
                          }}
                        >
                          {isDebit ? '- ' : '+ '}
                          {formatINR(tx.amount_paise)}
                        </div>
                      </td>

                      {/* Status */}
                      <td style={{ padding: '0.75rem 1rem', textAlign: 'center', whiteSpace: 'nowrap' }}>
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

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div
            style={{
              padding: '0.75rem 1.25rem',
              borderTop: '1px solid var(--color-border)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              backgroundColor: '#FAFAF8',
              fontSize: '0.75rem',
            }}
          >
            <span style={{ color: 'var(--color-text-secondary)' }}>
              Page <strong>{page + 1}</strong> of <strong>{totalPages}</strong>
            </span>

            <div style={{ display: 'flex', gap: '0.4rem' }}>
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="btn btn-secondary"
                style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem' }}
              >
                <ChevronLeft size={13} /> Previous
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="btn btn-secondary"
                style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem' }}
              >
                Next <ChevronRight size={13} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
