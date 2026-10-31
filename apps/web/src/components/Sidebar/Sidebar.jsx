import React from 'react';
import { Link, useRouter } from '../../router/Router';
import { useAuth } from '../../context/AuthContext';
import { homeForRole } from '../../lib/access';
import {
  Zap,
  LayoutDashboard,
  FilePlus,
  FileText,
  CreditCard,
  LifeBuoy,
  ClipboardList,
  Wrench,
  Package,
  Layers,
  CheckSquare,
  Users,
  BarChart3,
  Search,
} from 'lucide-react';
import './Sidebar.css';

const NAV_BY_ROLE = {
  customer: [
    { href: '/customer', label: 'My Enquiries', icon: <LayoutDashboard size={18} /> },
    { href: '/customer/enquiries/new', label: 'New Solar Enquiry', icon: <FilePlus size={18} /> },
    { href: '/customer/quotations', label: 'Quotations', icon: <FileText size={18} />, planned: true },
    { href: '/customer/payments', label: 'Payments', icon: <CreditCard size={18} />, planned: true },
    { href: '/customer/support', label: 'Help & Warranty', icon: <LifeBuoy size={18} />, planned: true },
  ],
  sales: [
    { href: '/sales', label: 'Solar Enquiries', icon: <ClipboardList size={18} /> },
    { href: '/sales/surveys', label: 'Site Surveys', icon: <Layers size={18} />, planned: true },
    { href: '/sales/quotations', label: 'Proposals & Quotes', icon: <FileText size={18} />, planned: true },
  ],
  technician: [
    { href: '/technician', label: 'Assigned Surveys', icon: <ClipboardList size={18} /> },
    { href: '/sales/surveys', label: 'Shadow Raytracing', icon: <Layers size={18} />, planned: true },
    { href: '/technician/repairs', label: 'Repairs & Maintenance', icon: <Wrench size={18} />, planned: true },
  ],
  warehouse_staff: [
    { href: '/warehouse', label: 'Solar Stock', icon: <Package size={18} /> },
    { href: '/warehouse/picking', label: 'Material Picking', icon: <Layers size={18} />, planned: true },
  ],
  warehouse_manager: [
    { href: '/warehouse', label: 'Solar Stock', icon: <Package size={18} /> },
    { href: '/warehouse/picking', label: 'Material Picking', icon: <Layers size={18} />, planned: true },
    { href: '/warehouse/approvals', label: 'Dispatches & Approvals', icon: <CheckSquare size={18} />, planned: true },
  ],
  support: [
    { href: '/support', label: 'Support Tickets', icon: <LifeBuoy size={18} /> },
    { href: '/support/lookup', label: 'Customer Lookup', icon: <Search size={18} />, planned: true },
  ],
  admin: [
    { href: '/admin', label: 'Employee Roster', icon: <Users size={18} /> },
    { href: '/sales', label: 'Solar Enquiries', icon: <ClipboardList size={18} /> },
    { href: '/admin/reports', label: 'Ops Intelligence', icon: <BarChart3 size={18} />, planned: true },
  ],
};

export function Sidebar({ isOpen, onClose }) {
  const { user } = useAuth();
  const { path } = useRouter();

  const role = user?.role || 'customer';
  const links = NAV_BY_ROLE[role] || NAV_BY_ROLE.customer;
  const brandHome = homeForRole(role);

  return (
    <>
      {isOpen && <div className="sidebar-overlay" onClick={onClose} />}

      <aside className={`sidebar-container ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-brand-box">
          <Link href={brandHome} className="sidebar-logo" onClick={onClose}>
            <div className="sidebar-logo-icon">
              <Zap size={20} fill="#000000" />
            </div>
            <span>SolarOps</span>
          </Link>
          <span className="sidebar-tagline">SunPower Solutions</span>
        </div>

        <nav className="sidebar-nav">
          <span className="sidebar-section-title">Operations Portal</span>
          {links.map((link) => {
            const isActive = path === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
                onClick={onClose}
              >
                <div className="sidebar-nav-item-left">
                  <span className="sidebar-nav-icon">{link.icon}</span>
                  <span>{link.label}</span>
                </div>
                {link.planned && <span className="sidebar-planned-tag">Planned</span>}
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-system-status">
            <span className="sidebar-system-status-dot" />
            <span>Grid Connected</span>
          </div>
          <span>v2.4.0</span>
        </div>
      </aside>
    </>
  );
}

