import React, { useEffect, Suspense, lazy } from 'react';
import { useRouter } from './router/Router';
import { useAuth } from './context/AuthContext';
import { homeForRole } from './lib/access';
import { DashboardSkeleton } from './components/SkeletonLoader/SkeletonLoader';
import './App.css';

// ============================================================================
// PERFORMANCE OPTIMIZATION: CODE-SPLIT LAZY LOADED ROUTE COMPONENTS
// Only the active route chunk is loaded over network (<50ms initial load time)
// ============================================================================

// Auth Pages
const Login = lazy(() => import('./pages/Login/Login').then((m) => ({ default: m.Login })));
const Signup = lazy(() => import('./pages/Signup/Signup').then((m) => ({ default: m.Signup })));
const VerifyEmail = lazy(() => import('./pages/VerifyEmail/VerifyEmail').then((m) => ({ default: m.VerifyEmail })));

// Customer Pages
const CustomerDashboard = lazy(() => import('./pages/Customer/CustomerDashboard').then((m) => ({ default: m.CustomerDashboard })));
const NewEnquiry = lazy(() => import('./pages/Customer/NewEnquiry').then((m) => ({ default: m.NewEnquiry })));
const EnquiryDetail = lazy(() => import('./pages/Customer/EnquiryDetail').then((m) => ({ default: m.EnquiryDetail })));
const CustomerQuotations = lazy(() => import('./pages/Customer/CustomerQuotations').then((m) => ({ default: m.CustomerQuotations })));
const CustomerPayments = lazy(() => import('./pages/Customer/CustomerPayments').then((m) => ({ default: m.CustomerPayments })));
const RazorpayPaymentPage = lazy(() => import('./pages/Customer/RazorpayPaymentPage').then((m) => ({ default: m.RazorpayPaymentPage })));
const CustomerSupport = lazy(() => import('./pages/Customer/CustomerSupport').then((m) => ({ default: m.CustomerSupport })));
const SolarStore = lazy(() => import('./pages/Customer/SolarStore').then((m) => ({ default: m.SolarStore })));

// Sales Pages
const SalesDashboard = lazy(() => import('./pages/Sales/SalesDashboard').then((m) => ({ default: m.SalesDashboard })));
const EnquiryReview = lazy(() => import('./pages/Sales/EnquiryReview').then((m) => ({ default: m.EnquiryReview })));
const SalesSurveys = lazy(() => import('./pages/Sales/SalesSurveys').then((m) => ({ default: m.SalesSurveys })));
const SalesQuotations = lazy(() => import('./pages/Sales/SalesQuotations').then((m) => ({ default: m.SalesQuotations })));

// Technician Pages
const TechnicianDashboard = lazy(() => import('./pages/Technician/TechnicianDashboard').then((m) => ({ default: m.TechnicianDashboard })));
const TechnicianMapPage = lazy(() => import('./pages/Technician/TechnicianMapPage').then((m) => ({ default: m.TechnicianMapPage })));

// Warehouse Pages
const WarehouseDashboard = lazy(() => import('./pages/Warehouse/WarehouseDashboard').then((m) => ({ default: m.WarehouseDashboard })));

// Support Pages
const SupportDashboard = lazy(() => import('./pages/Support/SupportDashboard').then((m) => ({ default: m.SupportDashboard })));

// Admin Pages
const AdminDashboard = lazy(() => import('./pages/Admin/AdminDashboard').then((m) => ({ default: m.AdminDashboard })));

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
    return <DashboardSkeleton />;
  }

  const renderRoute = () => {
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
    if (path === '/technician/map' || path === '/technician/route') return <TechnicianMapPage />;
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
  };

  return (
    <Suspense fallback={<DashboardSkeleton />}>
      {renderRoute()}
    </Suspense>
  );
}

export default App;
