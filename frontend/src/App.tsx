import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { TransactionsPage } from './pages/TransactionsPage';
import { TransferPage } from './pages/TransferPage';
import { SecurityConsolePage } from './pages/SecurityConsolePage';
import { AdminPage } from './pages/AdminPage';
import { ShieldCheck, Cpu, Radio } from 'lucide-react';

const AppContent: React.FC = () => {
  const { user, token, loading } = useAuth();
  const [currentPage, setCurrentPage] = useState<string>('dashboard');
  const [unauthView, setUnauthView] = useState<'landing' | 'login' | 'register'>('landing');

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          gap: '0.75rem',
          backgroundColor: 'var(--color-page-bg)',
          color: 'var(--color-text-secondary)',
        }}
      >
        <div
          style={{
            width: '32px',
            height: '32px',
            border: '2px solid var(--color-border)',
            borderTopColor: 'var(--color-primary-burgundy)',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }}
        />
        <span style={{ fontSize: '0.75rem', fontWeight: 500 }}>
          Loading BankSim...
        </span>
      </div>
    );
  }

  // Public / Unauthenticated Views
  if (!token || !user) {
    if (unauthView === 'login') {
      return (
        <LoginPage
          onSuccess={() => setCurrentPage('dashboard')}
          onNavigateToHome={() => setUnauthView('landing')}
          onNavigateToRegister={() => setUnauthView('register')}
        />
      );
    }

    if (unauthView === 'register') {
      return (
        <RegisterPage
          onSuccessToLogin={() => setUnauthView('login')}
          onNavigateToHome={() => setUnauthView('landing')}
          onNavigateToLogin={() => setUnauthView('login')}
        />
      );
    }

    return (
      <LandingPage
        onNavigateToLogin={() => setUnauthView('login')}
        onNavigateToRegister={() => setUnauthView('register')}
      />
    );
  }

  // Authenticated Portal View
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--color-page-bg)' }}>
      <Navbar currentPage={currentPage} onNavigate={setCurrentPage} />

      <main style={{ flex: 1, padding: '1.5rem 1.25rem', maxWidth: '1240px', width: '100%', margin: '0 auto' }}>
        {currentPage === 'dashboard' && (
          <DashboardPage onNavigate={setCurrentPage} />
        )}
        {currentPage === 'transactions' && (
          <TransactionsPage onNavigate={setCurrentPage} />
        )}
        {currentPage === 'transfer' && (
          <TransferPage onNavigate={setCurrentPage} />
        )}
        {currentPage === 'security' && (
          <SecurityConsolePage />
        )}
        {currentPage === 'admin' && (
          <AdminPage />
        )}
      </main>

      {/* Enterprise Security Footer */}
      <footer
        style={{
          borderTop: '1px solid var(--color-border)',
          padding: '0.75rem 1.25rem',
          marginTop: 'auto',
          backgroundColor: 'var(--color-surface)',
          fontSize: '0.75rem',
          color: 'var(--color-text-secondary)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', color: 'var(--color-text-main)', fontWeight: 600 }}>
            <ShieldCheck size={14} color="var(--color-primary-burgundy)" />
            <span>BankSim AI Firewall</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <Cpu size={13} />
            <span>Dual-Engine: Adaptive Risk & AI Memo Analysis</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', color: 'var(--color-success)' }}>
            <Radio size={13} />
            <span>Phase 7 Challenge Active</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '0.6875rem' }}>
            Session: <strong style={{ color: 'var(--color-text-main)' }}>{user.username}</strong> ({user.role})
          </span>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
              color: 'var(--color-success)',
              fontSize: '0.6875rem',
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: 'var(--color-success)',
                display: 'inline-block',
              }}
            />
            <span>Secured Session</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;
