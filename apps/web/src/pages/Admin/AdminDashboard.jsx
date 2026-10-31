import React, { useState, useEffect } from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { DashboardView } from '../../components/DashboardView/DashboardView';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { Badge } from '../../components/Badge/Badge';
import { Modal } from '../../components/Modal/Modal';
import { TextField } from '../../components/TextField/TextField';
import { SelectField } from '../../components/SelectField/SelectField';
import { LoadingState } from '../../components/LoadingState/LoadingState';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { ROLE_DISPLAY } from '../../lib/access';
import { Users, UserPlus, Shield, Activity, Database, Server, Plus, Clock } from 'lucide-react';
import './AdminDashboard.css';
import '../Customer/CustomerDashboard.css';

export function AdminDashboard() {
  const { showToast } = useAuth();
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);

  // New Employee Form
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('sales');

  const fetchEmployees = () => {
    setLoading(true);
    api.getEmployees().then((data) => {
      setEmployees(data);
      setLoading(false);
    });
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
    showToast({
      type: 'success',
      title: 'Staff Provisioned',
      message: `Staff account for ${fullName} provisioned successfully!`,
    });
  };

  return (
    <AppShell requiredRole="admin">
      {loading ? (
        <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <LoadingState label="Loading administration dashboard…" />
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          {/* Master Bento Dashboard for Admin */}
          <DashboardView
            role="admin"
            employees={employees}
            onNewAction={() => setModalOpen(true)}
          />

          {/* Operations Staff Roster Table */}
          <div className="bento-card" style={{ padding: '28px' }}>
            <div className="bento-card-header" style={{ marginBottom: '20px' }}>
              <div>
                <h3 className="bento-card-title">System Administration & Personnel Roster</h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '12.5px', color: '#64748b' }}>
                  Provision operations personnel, configure role-based access control, and inspect infrastructure telemetry.
                </p>
              </div>

              <button
                type="button"
                className="primary-board-btn"
                onClick={() => setModalOpen(true)}
              >
                <UserPlus size={16} />
                <span>Provision Employee</span>
              </button>
            </div>

            <div className="solar-table-container">
              <table className="solar-table">
                <thead>
                  <tr>
                    <th>Emp Code</th>
                    <th>Full Name</th>
                    <th>Email Address</th>
                    <th>Assigned Role</th>
                    <th>Permissions</th>
                    <th>Account Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {employees.map((emp) => (
                    <tr key={emp.id}>
                      <td>
                        <span style={{ fontFamily: 'monospace', fontWeight: '700', color: '#111827' }}>
                          {emp.employee_code}
                        </span>
                      </td>
                      <td>
                        <strong style={{ color: '#111827' }}>{emp.full_name}</strong>
                      </td>
                      <td style={{ color: '#64748b' }}>{emp.email}</td>
                      <td>
                        <Badge variant="lime">{ROLE_DISPLAY[emp.role] || emp.role}</Badge>
                      </td>
                      <td>
                        <span style={{ fontSize: '11px', color: '#475569', background: '#f1f5f9', padding: '3px 8px', borderRadius: '6px' }}>
                          RBAC: {emp.role.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#10b981', fontWeight: '600' }}>
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981' }} />
                          <span>Active</span>
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="bento-header-btn"
                          style={{ color: '#4f46e5', fontWeight: '700' }}
                          onClick={() => showToast({ type: 'info', title: 'Password Reset', message: `Password reset link dispatched for ${emp.employee_code}.` })}
                        >
                          <span>Reset</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Provision Employee Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Provision Operations Employee"
      >
        <form onSubmit={handleCreateEmployee}>
          <TextField
            label="Full Name"
            name="fullName"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="e.g. Sumanth Rao"
            required
          />

          <TextField
            label="Corporate Email Address"
            name="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="sumanth@sunpower.dev"
            required
          />

          <SelectField
            label="Operational Department & Role"
            name="role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            options={[
              { value: 'sales', label: 'Sales Feasibility Executive' },
              { value: 'technician', label: 'Field Technician / Surveyor' },
              { value: 'warehouse_staff', label: 'Warehouse Staff' },
              { value: 'warehouse_manager', label: 'Warehouse Manager' },
              { value: 'support', label: 'Support Specialist' },
              { value: 'admin', label: 'System Administrator' },
            ]}
          />

          <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button
              type="button"
              className="export-data-btn"
              onClick={() => setModalOpen(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="primary-board-btn"
            >
              Confirm Provisioning
            </button>
          </div>
        </form>
      </Modal>
    </AppShell>
  );
}

export default AdminDashboard;
