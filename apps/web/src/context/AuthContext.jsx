import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';
import { homeForRole } from '../lib/access';
import './AuthContext.css';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  };

  useEffect(() => {
    let isMounted = true;
    api
      .getMe()
      .then((body) => {
        if (isMounted) setUser(body.user);
      })
      .catch(() => {
        if (isMounted) setUser(null);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Fake Login instant bypass
  const bypassLogin = (roleKey) => {
    const newUser = api.bypassLogin(roleKey);
    setUser(newUser);
    showToast(`⚡ Demo Mode Active: Logged in as ${newUser.full_name} (${newUser.role.toUpperCase()})`);
    return newUser;
  };

  const login = async (identifier, password, accountKind = 'customer') => {
    const res = await api.login(identifier, password, accountKind);
    setUser(res.user);
    showToast(`Welcome back, ${res.user.full_name}!`);
    return res.user;
  };

  const signup = async (formData) => {
    return await api.signup(formData);
  };

  const verifyEmail = async (email, code) => {
    return await api.verifyEmail(email, code);
  };

  const logout = async () => {
    await api.logout();
    setUser(null);
    showToast('Signed out of SolarOps session.');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        signup,
        verifyEmail,
        bypassLogin,
        logout,
        showToast,
      }}
    >
      {children}
      {toastMessage && (
        <div className="auth-toast-container">
          <div className="auth-toast">
            <span>⚡</span>
            <span>{toastMessage}</span>
          </div>
        </div>
      )}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

