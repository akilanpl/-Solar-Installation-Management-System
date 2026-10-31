import React from 'react';
import { Modal } from '../Modal/Modal';
import { Button } from '../Button/Button';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from '../../router/Router';
import { FAKE_USERS } from '../../services/mockData';
import { homeForRole } from '../../lib/access';
import { Zap, UserCheck, Shield, HardHat, Warehouse, Headphones, Sparkles } from 'lucide-react';
import './FakeLoginModal.css';

const PERSONAS = [
  {
    key: 'customer',
    icon: <UserCheck size={18} color="#C6FF34" />,
    role: 'Customer',
    data: FAKE_USERS.customer,
    desc: 'Submit & track home/commercial solar enquiries',
  },
  {
    key: 'sales',
    icon: <Sparkles size={18} color="#7E3BED" />,
    role: 'Sales Executive',
    data: FAKE_USERS.sales,
    desc: 'Review, qualify & schedule customer solar leads',
  },
  {
    key: 'technician',
    icon: <HardHat size={18} color="#C6FF34" />,
    role: 'Field Technician',
    data: FAKE_USERS.technician,
    desc: 'Shadow ray tracing, roof load checks & site surveys',
  },
  {
    key: 'warehouse',
    icon: <Warehouse size={18} color="#7E3BED" />,
    role: 'Warehouse Manager',
    data: FAKE_USERS.warehouse,
    desc: 'Manage panels, hybrid inverters & battery dispatch',
  },
  {
    key: 'support',
    icon: <Headphones size={18} color="#C6FF34" />,
    role: 'Support Specialist',
    data: FAKE_USERS.support,
    desc: 'Net-metering, subsidy queries & warranty tickets',
  },
  {
    key: 'admin',
    icon: <Shield size={18} color="#7E3BED" />,
    role: 'Administrator',
    data: FAKE_USERS.admin,
    desc: 'Full ops oversight, employee provisioning & logs',
  },
];

export function FakeLoginModal({ isOpen, onClose }) {
  const { bypassLogin } = useAuth();
  const { navigate } = useRouter();

  const handleSelectRole = (roleKey) => {
    const user = bypassLogin(roleKey);
    onClose();
    navigate(homeForRole(user.role));
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <>
          <Zap size={20} color="#C6FF34" />
          <span>  Instant Fake Login (Demo Bypass)</span>
        </>
      }
      maxWidth="720px"
      footer={
        <Button variant="ghost" onClick={onClose}>
          Cancel
        </Button>
      }
    >
      <p style={{ marginBottom: '18px', fontSize: '13px', color: 'var(--color-white-dim)' }}>
        Select any persona below to immediately bypass authentication with mock session credentials.
        No database or password required:
      </p>

      <div className="fake-login-grid">
        {PERSONAS.map((p) => (
          <button
            key={p.key}
            type="button"
            className="fake-user-card"
            onClick={() => handleSelectRole(p.key)}
          >
            <div className="fake-user-header">
              {p.icon}
              <span className="fake-user-role-badge">{p.role}</span>
            </div>
            <div className="fake-user-name">{p.data.full_name}</div>
            <div className="fake-user-id">
              {p.data.employee_code || p.data.email}
            </div>
            <div className="fake-user-hint">
              <span>  Click to Enter</span>
            </div>
          </button>
        ))}
      </div>
    </Modal>
  );
}

