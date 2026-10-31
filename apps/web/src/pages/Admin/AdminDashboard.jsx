import React, { useState, useEffect } from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { Badge } from '../../components/Badge/Badge';
import { Modal } from '../../components/Modal/Modal';
import { TextField } from '../../components/TextField/TextField';
import { SelectField } from '../../components/SelectField/SelectField';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { ROLE_DISPLAY } from '../../lib/access';
import { Users, UserPlus, Shield, Activity, Database, Server } from 'lucide-react';
import './AdminDashboard.css';
import '../Customer/CustomerDashboard.css';

export function AdminDashboard() {
  const { showToast } = useAuth();
  const [employees, setEmployees] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);

  // New Employee Form
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('sales');

  const fetchEmployees = () => {
    api.getEmployees().then(setEmployees);
  };

  useEffect(() => {
    fetchEmployees();
  }, []);

  const handleCreateEmployee = async (e) => {
    e.preventDefault();
    await api.createEmployee({
      full_name: fullName,
      email,
      role,
    });
    setModalOpen(false);
    setFullName('');
    setEmail('');
    fetchEmployees();
    showToast(`Staff account for ${fullName} provisioned successfully!`);
  };

  return (
    <AppShell requiredRole="admin">
      <PageHeader
        title="System Administration & Staff Roster"
        description="Provision operations personnel, configure role-based access control, and inspect infrastructure telemetry."
        action={
          <Button
            variant="primary"
            icon={<UserPlus size={16} />}
            onClick={() => setModalOpen(true)}
          >
            Provision Employee
          </Button>
        }
      />

      {/* System Telemetry Row */}
      <div className="health-metrics-grid">
        <Card accent="lime">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-white-dim)' }}>PostgreSQL Database</span>
            <div className="health-status-badge">
              <span className="health-pulse" />
              <span>Healthy</span>
            </div>
          </div>
          <div style={{ fontSize: '20px', fontWeight: '800', marginTop: '8px' }}>
            Port 5432 · Active Pool
          </div>
          <span style={{ fontSize: '11px', color: 'var(--color-white-faint)', marginTop: '4px', display: 'block' }}>
            Alembic Head: 001_phase1_foundation
          </span>
        </Card>

        <Card accent="violet">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-white-dim)' }}>FastAPI Gateway</span>
            <div className="health-status-badge">
              <span className="health-pulse" />
              <span>Online</span>
            </div>
          </div>
          <div style={{ fontSize: '20px', fontWeight: '800', marginTop: '8px' }}>
            /api/v1 · Uvicorn
          </div>
          <span style={{ fontSize: '11px', color: 'var(--color-white-faint)', marginTop: '4px', display: 'block' }}>
            CSRF + Strict Cookie Isolation
          </span>
        </Card>

        <Card accent="lime">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-white-dim)' }}>Active Workforce</span>
            <span style={{ fontSize: '12px', color: 'var(--color-lime)', fontWeight: '700' }}>
              {employees.length} Staff Members
            </span>
          </div>
          <div style={{ fontSize: '20px', fontWeight: '800', marginTop: '8px' }}>
            6 Departments
          </div>
          <span style={{ fontSize: '11px', color: 'var(--color-white-faint)', marginTop: '4px', display: 'block' }}>
            Zero access violations logged
          </span>
        </Card>
      </div>

      {/* Employee Management Roster */}
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: '700' }}>Enterprise Employee Directory</h3>
          <span style={{ fontSize: '13px', color: 'var(--color-white-dim)' }}>
            Staff authenticate via Employee Code (EMP-XXX-001)
          </span>
        </div>

        <div className="solar-table-container">
          <table className="solar-table">
            <thead>
              <tr>
                <th>Employee Code</th>
                <th>Staff Member</th>
                <th>Portal Role</th>
                <th>Internal Email</th>
                <th>Status</th>
                <th>Joined</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {employees.map((emp) => (
                <tr key={emp.id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', color: 'var(--color-lime)' }}>
                    {emp.employee_code}
                  </td>
                  <td style={{ fontWeight: '600', color: 'var(--color-white)' }}>{emp.full_name}</td>
                  <td>
                    <Badge variant="violet">
                      {ROLE_DISPLAY[emp.role] || emp.role}
                    </Badge>
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{emp.email}</td>
                  <td>
                    <Badge variant="success">Active</Badge>
                  </td>
                  <td>{emp.joined}</td>
                  <td>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => showToast(`Password reset link dispatched for ${emp.employee_code}`)}
                    >
                      Reset Key
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Provision Employee Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Provision New Operations Staff Member"
        footer={null}
      >
        <form onSubmit={handleCreateEmployee}>
          <TextField
            label="Full Employee Name"
            name="fullName"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="e.g. Anand Murthy"
            required
          />

          <TextField
            label="SunPower Work Email"
            name="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="anand.m@sunpowersolutions.com"
            required
          />

          <SelectField
            label="Departmental Role"
            name="role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            required
          >
            <option value="sales">Sales Executive</option>
            <option value="technician">Field Site Technician</option>
            <option value="warehouse_manager">Warehouse Manager</option>
            <option value="warehouse_staff">Warehouse Logistics Staff</option>
            <option value="support">Customer Support Specialist</option>
            <option value="admin">System Administrator</option>
          </SelectField>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <Button variant="ghost" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Generate Employee Account
            </Button>
          </div>
        </form>
      </Modal>
    </AppShell>
  );
}

