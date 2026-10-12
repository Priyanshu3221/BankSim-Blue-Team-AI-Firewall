import React, { createContext, useContext, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { LoginChallengeResponse, ResendOtpResponse, User } from '../api/types';

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  initiateLogin: (username: string, password: string) => Promise<LoginChallengeResponse>;
  verifyLogin: (challengeId: number, otpCode: string) => Promise<User>;
  resendLoginOtp: (challengeId: number) => Promise<ResendOtpResponse>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('banksim_token'));
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadUser() {
      const storedToken = localStorage.getItem('banksim_token');
      if (!storedToken) {
        setLoading(false);
        return;
      }

      try {
        const currentUser = await api.getCurrentUser();
        setUser(currentUser);
      } catch (err) {
        console.warn('Session expired or invalid, logging out', err);
        localStorage.removeItem('banksim_token');
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, [token]);

  const initiateLogin = async (username: string, password: string): Promise<LoginChallengeResponse> => {
    return await api.login(username, password);
  };

  const verifyLogin = async (challengeId: number, otpCode: string): Promise<User> => {
    const res = await api.verifyLoginOtp({
      challenge_id: challengeId,
      verification_code: otpCode.trim(),
    });

    // Store token ONLY after successful OTP verification
    localStorage.setItem('banksim_token', res.access_token);
    setToken(res.access_token);

    let userData = res.user;
    if (!userData) {
      userData = await api.getCurrentUser();
    }
    setUser(userData);
    return userData;
  };

  const resendLoginOtp = async (challengeId: number): Promise<ResendOtpResponse> => {
    return await api.resendLoginOtp({ challenge_id: challengeId });
  };

  const logout = () => {
    localStorage.removeItem('banksim_token');
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    if (!token) return;
    try {
      const updated = await api.getCurrentUser();
      setUser(updated);
    } catch {
      logout();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        initiateLogin,
        verifyLogin,
        resendLoginOtp,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
