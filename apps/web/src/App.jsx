import React, { useEffect } from 'react';
import { useRouter } from './router/Router';
import { useAuth } from './context/AuthContext';
import { homeForRole } from './lib/access';

// Auth Pages
import { Login } from './pages/Login/Login';
import { Signup } from './pages/Signup/Signup';
import { VerifyEmail } from './pages/VerifyEmail/VerifyEmail';

// Customer Pages
import { CustomerDashboard } from './pages/Customer/CustomerDashboard';
import { NewEnquiry } from './pages/Customer/NewEnquiry';
import { EnquiryDetail } from './pages/Customer/EnquiryDetail';
import { CustomerQuotations } from './pages/Customer/CustomerQuotations';
import { CustomerPayments } from './pages/Customer/CustomerPayments';
import { RazorpayPaymentPage } from './pages/Customer/RazorpayPaymentPage';
import { CustomerSupport } from './pages/Customer/CustomerSupport';
import { SolarStore } from './pages/Customer/SolarStore';

// Sales Pages
import { SalesDashboard } from './pages/Sales/SalesDashboard';
import { EnquiryReview } from './pages/Sales/EnquiryReview';
import { SalesSurveys } from './pages/Sales/SalesSurveys';
import { SalesQuotations } from './pages/Sales/SalesQuotations';

// Technician Pages
import { TechnicianDashboard } from './pages/Technician/TechnicianDashboard';

// Warehouse Pages
import { WarehouseDashboard } from './pages/Warehouse/WarehouseDashboard';

// Support Pages
import { SupportDashboard } from './pages/Support/SupportDashboard';

// Admin Pages
import { AdminDashboard } from './pages/Admin/AdminDashboard';

import { LoadingState } from './components/LoadingState/LoadingState';
import './App.css';

export function App() {
  const { path, navigate } = useRouter();
  const { user, loading } = useAuth();

  // Root redirect logic
  useEffect(() => {
    if (path === '/' && !loading) {
      if (user) {
        navigate(homeForRole(user.role));
      } else {
        navigate('/login');
      }
    }
  }, [path, user, loading, navigate]);

  if (loading && path === '/') {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <LoadingState label="Starting SolarOps Operations…" />
      </div>
    );
  }

  // Auth Routes
  if (path === '/login') return <Login />;
  if (path === '/signup') return <Signup />;
  if (path.startsWith('/verify-email')) return <VerifyEmail />;

  // Customer Routes
  if (path === '/customer') return <CustomerDashboard />;
  if (path === '/customer/store' || path === '/customer/ecommerce' || path === '/store') return <SolarStore />;
  if (path === '/customer/enquiries/new') return <NewEnquiry />;
  if (path.startsWith('/customer/enquiries/')) {
    const enquiryId = path.split('/customer/enquiries/')[1];
    return <EnquiryDetail enquiryId={enquiryId} />;
  }
  if (path === '/customer/quotations') return <CustomerQuotations />;
  if (path === '/customer/payments/razorpay') return <RazorpayPaymentPage />;
  if (path === '/customer/payments') return <CustomerPayments />;
  if (path === '/customer/support') return <CustomerSupport />;

  // Sales Routes
  if (path === '/sales') return <SalesDashboard />;
  if (path.startsWith('/sales/enquiries/')) {
    const enquiryId = path.split('/sales/enquiries/')[1];
    return <EnquiryReview enquiryId={enquiryId} />;
  }
  if (path === '/sales/surveys') return <SalesSurveys />;
  if (path === '/sales/quotations') return <SalesQuotations />;

  // Technician Routes
  if (path === '/technician' || path === '/technician/repairs') return <TechnicianDashboard />;
  if (path === '/technician/surveys') return <SalesSurveys />;

  // Warehouse Routes
  if (path === '/warehouse' || path === '/warehouse/picking' || path === '/warehouse/approvals') {
    return <WarehouseDashboard />;
  }

  // Support Routes
  if (path === '/support' || path === '/support/lookup') return <SupportDashboard />;

  // Admin Routes
  if (path === '/admin' || path === '/admin/reports') return <AdminDashboard />;

  // Fallback
  return user ? <CustomerDashboard /> : <Login />;
}

