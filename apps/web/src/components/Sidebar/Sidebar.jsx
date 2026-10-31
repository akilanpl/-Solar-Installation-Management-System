import React, { useState } from 'react';
import { Link, useRouter } from '../../router/Router';
import { useAuth } from '../../context/AuthContext';
import { homeForRole } from '../../lib/access';
import { FakeLoginModal } from '../FakeLoginModal/FakeLoginModal';
import { SolarChatbot } from '../SolarChatbot/SolarChatbot';
import { EquipmentScannerModal } from '../EquipmentScannerModal/EquipmentScannerModal';
import {
  LayoutDashboard,
  FileText,
  CreditCard,
  Headphones,
  Calendar,
  Layers,
  Wrench,
  Package,
  Shield,
  PlusCircle,
  Zap,
  LogOut,
  ShoppingBag,
  Navigation,
  ScanBarcode,
} from 'lucide-react';
import dockAiIcon from '../../assets/dock-ai-icon.png';
import './Sidebar.css';

export function Sidebar() {
  const { user, logout, showToast } = useAuth();
  const { path, navigate } = useRouter();
  const [fakeModalOpen, setFakeModalOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [scannerOpen, setScannerOpen] = useState(false);

  const homePath = user ? homeForRole(user.role) : '/login';
  const role = user?.role || 'customer';

  // Scanner permission: warehouse managers/staff to maintain stock, technicians to verify work, admin to audit both
  const canScan =
    role === 'warehouse_manager' ||
    role === 'warehouse_staff' ||
    role === 'technician' ||
    role === 'admin';

  const scannerTitle =
    role === 'technician'
      ? 'Field Work Verification Scanner (Verify BOM & Installation)'
      : role === 'warehouse_manager' || role === 'warehouse_staff'
      ? 'Warehouse Stock Scanner (Maintain Inventory & Staging)'
      : 'Optical Equipment & Stock Verification Scanner';

  // Build role-tailored essential navigation items
  const getNavItems = () => {
    switch (role) {
      case 'sales':
        return [
          { href: '/sales', label: 'Dashboard & Leads', icon: LayoutDashboard },
          { href: '/sales/surveys', label: 'Site Feasibility Surveys', icon: Calendar },
          { href: '/sales/quotations', label: 'BOM Quotations', icon: FileText },
        ];

      case 'technician':
        return [
          { href: '/technician', label: 'Dashboard & Work Orders', icon: LayoutDashboard },
          { href: '/technician/map', label: 'Field Route & GPS Map', icon: Navigation },
          { href: '/technician/surveys', label: 'Scheduled Field Surveys', icon: Calendar },
        ];

      case 'warehouse_staff':
      case 'warehouse_manager':
        return [
          { href: '/warehouse', label: 'Dashboard & Inventory', icon: LayoutDashboard },
        ];

      case 'support':
        return [
          { href: '/support', label: 'Dashboard & Customer Lookup', icon: LayoutDashboard },
        ];

      case 'admin':
        return [
          { href: '/admin', label: 'Administration & Roster', icon: LayoutDashboard },
          { href: '/customer/store', label: 'Hardware Marketplace', icon: ShoppingBag },
          { href: '/sales', label: 'Sales Operations', icon: Layers },
          { href: '/sales/surveys', label: 'Surveys Schedule', icon: Calendar },
          { href: '/warehouse', label: 'Inventory Logistics', icon: Package },
          { href: '/support', label: 'Customer Support Desk', icon: Headphones },
        ];

      case 'customer':
      default:
        return [
          { href: '/customer', label: 'Solar Dashboard', icon: LayoutDashboard },
          { href: '/customer/store', label: 'Solar Store & Hardware', icon: ShoppingBag },
          { href: '/customer/enquiries/new', label: 'New Solar Enquiry', icon: PlusCircle },
          { href: '/customer/quotations', label: 'Proposals & BOM', icon: FileText },
          { href: '/customer/payments', label: 'Milestone Payments', icon: CreditCard },
          { href: '/customer/support', label: 'Support & Warranty', icon: Headphones },
        ];
    }
  };

  const navItems = getNavItems();

  const handleLogout = () => {
    logout();
    navigate('/login');
    showToast({
      type: 'info',
      title: 'Signed Out',
      message: 'You have been signed out of SolarOps.',
    });
  };

  return (
    <>
      <aside className={`dock-sidebar-container liquid-glass-dock ${isChatOpen ? 'chat-expanded' : ''}`} aria-label="Quick Dock Navigation">
        {/* Liquid Glass Ambient Specular Sheen */}
        <div className="liquid-glass-specular-sheen" />

        {/* Top Nav Column */}
        <div className="dock-nav-column">
          {navItems.map((item, idx) => {
            const Icon = item.icon;
            const isActive = path === item.href;

            return (
              <Link
                key={idx}
                href={item.href}
                className={isActive ? 'dock-item-active' : 'dock-nav-btn'}
                title={item.label}
              >
                <Icon size={20} strokeWidth={2.2} />
                {isActive && <span className="dock-active-glow" />}
              </Link>
            );
          })}

          {/* Optical Scanner Button for Warehouse & Technician */}
          {canScan && (
            <button
              type="button"
              className={`dock-nav-btn dock-scan-btn ${scannerOpen ? 'active' : ''}`}
              title={scannerTitle}
              onClick={() => setScannerOpen(true)}
            >
              <ScanBarcode size={20} strokeWidth={2.2} />
              <span className="dock-scan-badge">SCAN</span>
            </button>
          )}

          {/* AI Copilot & Problem Resolver Button */}
          <button
            type="button"
            className={`dock-nav-btn dock-ai-btn ${isChatOpen ? 'active' : ''}`}
            title="SolarFlow AI Assistant (Diagnostics, Complaints & Orders)"
            onClick={() => setIsChatOpen(!isChatOpen)}
          >
            <img
              src={dockAiIcon}
              alt="SolarFlow AI"
              className="dock-ai-png-icon"
              draggable="false"
            />
            <span className="dock-ai-badge">AI</span>
          </button>
        </div>

        {/* Bottom Actions Column: Role Switcher & Logout */}
        <div className="dock-bottom-column">
          {/* Quick Persona Switcher */}
          <button
            type="button"
            className="dock-nav-btn"
            title="Switch Demo Role"
            onClick={() => setFakeModalOpen(true)}
          >
            <Zap size={19} color="#fbbf24" strokeWidth={2.4} />
          </button>

          {/* Logout */}
          <button
            type="button"
            className="dock-bottom-btn"
            title="Sign Out"
            onClick={handleLogout}
          >
            <LogOut size={17} />
          </button>
        </div>
      </aside>

      {/* Floating SolarChatbot Pane (Slides from right, toggled by AI dock icon) */}
      <SolarChatbot isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />

      {/* Modal View for Full Persona Switcher */}
      <FakeLoginModal
        isOpen={fakeModalOpen}
        onClose={() => setFakeModalOpen(false)}
      />

      {/* Optical Equipment Scanner & Work Verification Modal */}
      <EquipmentScannerModal
        isOpen={scannerOpen}
        onClose={() => setScannerOpen(false)}
        role={role}
      />
    </>
  );
}

export default Sidebar;
