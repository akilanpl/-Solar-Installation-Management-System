import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';
import { homeForRole } from '../lib/access';
import { Alert } from '../components/Alert/Alert';
import './AuthContext.css';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [toastConfig, setToastConfig] = useState(null);

  const showToast = (content, options = {}) => {
    let type = 'success';
    let title = 'Success';
    let message = '';

    if (typeof content === 'object' && content !== null) {
      type = content.type || 'success';
      title = content.title || (type === 'success' ? 'Success message' : type === 'warning' ? 'Warning message' : type === 'error' ? 'Error message' : 'Info message');
      message = content.message || content.subText || '';
    } else if (typeof content === 'string') {
      const lower = content.toLowerCase();
      if (lower.includes('demo mode active')) {
        type = 'success';
        title = 'Demo Mode Active';
        message = content.replace(/^ ?\s*demo mode active:?\s*/i, '');
      } else if (lower.includes('error') || lower.includes('failed') || lower.includes('invalid') || lower.includes('denied') || lower.includes('unable')) {
        type = 'error';
        title = options.title || 'Error message';
        message = content;
      } else if (lower.includes('warning') || lower.includes('caution') || lower.includes('check')) {
        type = 'warning';
        title = options.title || 'Warning message';
        message = content;
      } else if (lower.includes('signed out') || lower.includes('dispatched') || lower.includes('info')) {
        type = 'info';
        title = options.title || 'Info message';
        message = content;
      } else {
        type = options.type || 'success';
        title = options.title || 'Success message';
        message = content;
      }
    }

    setToastConfig({ type, title, message });

    if (window._toastTimeout) {
      clearTimeout(window._toastTimeout);
    }
    window._toastTimeout = setTimeout(() => {
      setToastConfig(null);
    }, 4500);
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
    showToast({
      type: 'success',
      title: 'Demo Mode Active',
      message: `Logged in as ${newUser.full_name} (${newUser.role.toUpperCase()})`,
    });
    return newUser;
  };

  const login = async (identifier, password, accountKind = 'customer') => {
    const res = await api.login(identifier, password, accountKind);
    setUser(res.user);
    showToast({
      type: 'success',
      title: 'Welcome Back',
      message: `Signed in as ${res.user.full_name}`,
    });
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
    showToast({
      type: 'info',
      title: 'Signed Out',
      message: 'SolarOps session ended.',
    });
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
      {toastConfig && (
        <div className="auth-toast-container">
          <Alert
            type={toastConfig.type}
            title={toastConfig.title}
            message={toastConfig.message}
            onClose={() => setToastConfig(null)}
          />
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
