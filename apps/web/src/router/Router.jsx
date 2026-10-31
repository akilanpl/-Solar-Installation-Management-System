import React, { createContext, useContext, useState, useEffect } from 'react';
import './Router.css';

const RouterContext = createContext(null);

export function RouterProvider({ children }) {
  const [currentPath, setCurrentPath] = useState(
    () => window.location.pathname || '/'
  );

  useEffect(() => {
    const onLocationChange = () => {
      setCurrentPath(window.location.pathname);
    };

    window.addEventListener('popstate', onLocationChange);
    return () => {
      window.removeEventListener('popstate', onLocationChange);
    };
  }, []);

  const navigate = (to) => {
    if (to === currentPath) return;
    window.history.pushState({}, '', to);
    setCurrentPath(to.split('?')[0]);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Parse query parameters
  const getQuery = () => {
    const params = new URLSearchParams(window.location.search);
    const obj = {};
    for (const [key, val] of params.entries()) {
      obj[key] = val;
    }
    return obj;
  };

  return (
    <RouterContext.Provider value={{ path: currentPath, navigate, query: getQuery() }}>
      {children}
    </RouterContext.Provider>
  );
}

export function useRouter() {
  const context = useContext(RouterContext);
  if (!context) {
    throw new Error('useRouter must be used within a RouterProvider');
  }
  return context;
}

export function Link({ href, className = '', children, onClick, ...props }) {
  const { path, navigate } = useRouter();
  const isActive = path === href;

  const handleClick = (e) => {
    if (e.metaKey || e.ctrlKey) return; // Allow open in new tab
    e.preventDefault();
    if (onClick) onClick(e);
    navigate(href);
  };

  return (
    <a
      href={href}
      onClick={handleClick}
      className={`nav-link ${isActive ? 'active' : ''} ${className}`}
      {...props}
    >
      {children}
    </a>
  );
}

