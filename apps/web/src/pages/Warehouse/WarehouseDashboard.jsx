import React, { useState, useEffect } from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { DashboardView } from '../../components/DashboardView/DashboardView';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { Badge } from '../../components/Badge/Badge';
import { LoadingState } from '../../components/LoadingState/LoadingState';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { Package, Plus, AlertTriangle, Layers, Truck, CheckSquare } from 'lucide-react';
import './WarehouseDashboard.css';
import '../Customer/CustomerDashboard.css';

export function WarehouseDashboard() {
  const { showToast } = useAuth();
  const [stock, setStock] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getStock().then((data) => {
      setStock(data);
      setLoading(false);
    });
  }, []);

  const totalUnits = stock.reduce((acc, s) => acc + (s.in_stock || 0), 0);
  const totalAllocated = stock.reduce((acc, s) => acc + (s.allocated || 0), 0);

  return (
    <AppShell>
      {loading ? (
        <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <LoadingState label="Loading warehouse inventory…" />
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          {/* Master Bento Dashboard for Warehouse */}
          <DashboardView
            role="warehouse_manager"
            stock={stock}
            onNewAction={() => showToast({ type: 'info', title: 'GRN Intake', message: 'Inbound stock receiving intake opened.' })}
          />

          {/* Physical Inventory & Staging Table */}
          <div className="bento-card" style={{ padding: '28px' }}>
            <div className="bento-card-header" style={{ marginBottom: '20px' }}>
              <div>
                <h3 className="bento-card-title">Photovoltaic Modules & Inverters Inventory</h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '12.5px', color: '#64748b' }}>
                  Track serial numbers, available stock, and allocated quantities for installation dispatches.
                </p>
              </div>

              <button
                type="button"
                className="primary-board-btn"
                onClick={() => showToast({ type: 'info', title: 'Stock Intake', message: 'Stock receiving GRN intake modal opened.' })}
              >
                <Plus size={16} />
                <span>Receive Inbound Stock</span>
              </button>
            </div>

            <div className="solar-table-container">
              <table className="solar-table">
                <thead>
                  <tr>
                    <th>SKU Code</th>
                    <th>Component Name</th>
                    <th>Category</th>
                    <th>In Stock</th>
                    <th>Allocated</th>
                    <th>Available</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {stock.map((item) => {
                    const available = (item.in_stock || 0) - (item.allocated || 0);
                    const isLow = available < 10;
                    return (
                      <tr key={item.sku}>
                        <td>
                          <span style={{ fontFamily: 'monospace', fontWeight: '700', color: '#111827' }}>
                            {item.sku}
                          </span>
                        </td>
                        <td>
                          <div style={{ fontWeight: '600', color: '#111827' }}>{item.name}</div>
                          <div style={{ fontSize: '12px', color: '#64748b' }}>{item.description}</div>
                        </td>
                        <td>
                          <span className="tag-badge">{item.category}</span>
                        </td>
                        <td style={{ fontWeight: '700', color: '#111827' }}>{item.in_stock}</td>
                        <td style={{ color: '#4f46e5', fontWeight: '600' }}>{item.allocated}</td>
                        <td>
                          <strong style={{ color: isLow ? '#ef4444' : '#10b981' }}>{available}</strong>
                        </td>
                        <td>
                          <Badge variant={isLow ? 'warning' : 'success'}>
                            {isLow ? 'Low Stock' : 'Optimal'}
                          </Badge>
                        </td>
                        <td>
                          <button
                            type="button"
                            className="bento-header-btn"
                            style={{ color: '#4f46e5', fontWeight: '700' }}
                            onClick={() => showToast({ type: 'success', title: 'Picking Slip', message: `Picking slip generated for ${item.sku}.` })}
                          >
                            <span>Pick Slip</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}

export default WarehouseDashboard;
