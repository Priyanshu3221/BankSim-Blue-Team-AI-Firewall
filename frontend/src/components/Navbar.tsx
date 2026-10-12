import React from 'react';
import { Shield, Landmark, ArrowRightLeft, ShieldAlert, UserCheck, LogOut, History } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface NavbarProps {
  currentPage: string;
  onNavigate: (page: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentPage, onNavigate }) => {
  const { user, logout } = useAuth();

  return (
    <header style={{
      backgroundColor: 'var(--color-primary-burgundy)',
      borderBottom: '1px solid rgba(229, 221, 216, 0.2)',
      position: 'sticky',
      top: 0,
      zIndex: 40,
    }}>
      <div style={{
        maxWidth: '1240px',
        margin: '0 auto',
        padding: '0.625rem 1.25rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.75rem',
      }}>
        {/* Brand */}
        <div 
          onClick={() => onNavigate('dashboard')}
          style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', cursor: 'pointer' }}
        >
          <div style={{
            backgroundColor: 'rgba(255, 255, 255, 0.12)',
            border: '1px solid rgba(229, 221, 216, 0.25)',
            width: '32px',
            height: '32px',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Shield size={17} color="#FFFFFF" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF', letterSpacing: '-0.01em' }}>
                BankSim
              </span>
              <span style={{
                fontSize: '0.625rem',
                fontWeight: 600,
                color: '#F7F3F0',
                backgroundColor: 'rgba(154, 89, 104, 0.45)',
                padding: '0.1rem 0.35rem',
                borderRadius: '3px',
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
              }}>
                Firewall
              </span>
            </div>
            <div style={{ fontSize: '0.6875rem', color: '#D6CBC5' }}>
              Defensive AI Banking Simulator
            </div>
          </div>
        </div>

        {/* Navigation links */}
        {user && (
          <nav style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', flexWrap: 'wrap' }}>
            <button
              onClick={() => onNavigate('dashboard')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.4rem 0.75rem',
                fontSize: '0.8125rem',
                fontWeight: 500,
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                backgroundColor: currentPage === 'dashboard' ? 'rgba(255, 255, 255, 0.16)' : 'transparent',
                color: currentPage === 'dashboard' ? '#FFFFFF' : '#E5DDD8',
                transition: 'background-color 0.15s ease, color 0.15s ease',
              }}
              onMouseEnter={(e) => {
                if (currentPage !== 'dashboard') {
                  e.currentTarget.style.backgroundColor = 'rgba(154, 89, 104, 0.25)';
                  e.currentTarget.style.color = '#FFFFFF';
                }
              }}
              onMouseLeave={(e) => {
                if (currentPage !== 'dashboard') {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = '#E5DDD8';
                }
              }}
            >
              <Landmark size={14} /> Dashboard
            </button>
            <button
              onClick={() => onNavigate('transactions')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.4rem 0.75rem',
                fontSize: '0.8125rem',
                fontWeight: 500,
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                backgroundColor: currentPage === 'transactions' ? 'rgba(255, 255, 255, 0.16)' : 'transparent',
                color: currentPage === 'transactions' ? '#FFFFFF' : '#E5DDD8',
                transition: 'background-color 0.15s ease, color 0.15s ease',
              }}
              onMouseEnter={(e) => {
                if (currentPage !== 'transactions') {
                  e.currentTarget.style.backgroundColor = 'rgba(154, 89, 104, 0.25)';
                  e.currentTarget.style.color = '#FFFFFF';
                }
              }}
              onMouseLeave={(e) => {
                if (currentPage !== 'transactions') {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = '#E5DDD8';
                }
              }}
            >
              <History size={14} /> Transactions
            </button>
            <button
              onClick={() => onNavigate('transfer')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.4rem 0.75rem',
                fontSize: '0.8125rem',
                fontWeight: 500,
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                backgroundColor: currentPage === 'transfer' ? 'rgba(255, 255, 255, 0.16)' : 'transparent',
                color: currentPage === 'transfer' ? '#FFFFFF' : '#E5DDD8',
                transition: 'background-color 0.15s ease, color 0.15s ease',
              }}
              onMouseEnter={(e) => {
                if (currentPage !== 'transfer') {
                  e.currentTarget.style.backgroundColor = 'rgba(154, 89, 104, 0.25)';
                  e.currentTarget.style.color = '#FFFFFF';
                }
              }}
              onMouseLeave={(e) => {
                if (currentPage !== 'transfer') {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = '#E5DDD8';
                }
              }}
            >
              <ArrowRightLeft size={14} /> Transfers
            </button>
            <button
              onClick={() => onNavigate('security')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.4rem 0.75rem',
                fontSize: '0.8125rem',
                fontWeight: 500,
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                backgroundColor: currentPage === 'security' ? 'rgba(255, 255, 255, 0.16)' : 'transparent',
                color: currentPage === 'security' ? '#FFFFFF' : '#E5DDD8',
                transition: 'background-color 0.15s ease, color 0.15s ease',
              }}
              onMouseEnter={(e) => {
                if (currentPage !== 'security') {
                  e.currentTarget.style.backgroundColor = 'rgba(154, 89, 104, 0.25)';
                  e.currentTarget.style.color = '#FFFFFF';
                }
              }}
              onMouseLeave={(e) => {
                if (currentPage !== 'security') {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = '#E5DDD8';
                }
              }}
            >
              <ShieldAlert size={14} /> Security Console
            </button>
            <button
              onClick={() => onNavigate('admin')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.4rem 0.75rem',
                fontSize: '0.8125rem',
                fontWeight: 500,
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                backgroundColor: currentPage === 'admin' ? 'rgba(255, 255, 255, 0.16)' : 'transparent',
                color: currentPage === 'admin' ? '#FFFFFF' : '#E5DDD8',
                transition: 'background-color 0.15s ease, color 0.15s ease',
              }}
              onMouseEnter={(e) => {
                if (currentPage !== 'admin') {
                  e.currentTarget.style.backgroundColor = 'rgba(154, 89, 104, 0.25)';
                  e.currentTarget.style.color = '#FFFFFF';
                }
              }}
              onMouseLeave={(e) => {
                if (currentPage !== 'admin') {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = '#E5DDD8';
                }
              }}
              title="SecOps Administration (Backend RBAC Enforced)"
            >
              <UserCheck size={14} /> Admin Console
            </button>
          </nav>
        )}

        {/* User profile & logout */}
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#FFFFFF' }}>{user.username}</div>
              <div style={{
                fontSize: '0.6875rem',
                color: user.role === 'ADMIN' ? '#FCA5A5' : '#E5DDD8',
                fontWeight: 500,
              }}>
                {user.role} • #{user.id}
              </div>
            </div>
            <button
              onClick={logout}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '0.35rem 0.5rem',
                borderRadius: '4px',
                border: '1px solid rgba(229, 221, 216, 0.25)',
                backgroundColor: 'rgba(255, 255, 255, 0.08)',
                color: '#E5DDD8',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
              title="Sign out"
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(154, 89, 104, 0.35)';
                e.currentTarget.style.color = '#FFFFFF';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)';
                e.currentTarget.style.color = '#E5DDD8';
              }}
            >
              <LogOut size={14} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
