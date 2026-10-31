import React, { useState, useEffect } from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { Badge } from '../../components/Badge/Badge';
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
      <PageHeader
        title="Warehouse Inventory & Logistics"
        description="Monitor physical stock counts of photovoltaic modules, hybrid inverters, batteries, and staging dispatches."
        action={
          <Button
            variant="primary"
            icon={<Plus size={16} />}
            onClick={() => showToast('Stock receiving GRN intake modal opened.')}
          >
            Receive Inbound Stock
          </Button>
        }
      />

      {/* KPI Stats Grid */}
      <div className="stats-grid-4">
        <Card className="stat-card-kpi">
          <div className="stat-icon-wrapper stat-icon-lime">
            <Package size={24} />
          </div>
          <div className="stat-kpi-info">
            <span className="stat-kpi-value">{totalUnits}</span>
            <span className="stat-kpi-label">Total Units on Hand</span>
          </div>
        </Card>

        <Card className="stat-card-kpi">
          <div className="stat-icon-wrapper stat-icon-violet">
            <Truck size={24} />
          </div>
          <div className="stat-kpi-info">
            <span className="stat-kpi-value">{totalAllocated}</span>
            <span className="stat-kpi-label">Units Allocated to Field</span>
          </div>
        </Card>

        <Card className="stat-card-kpi">
          <div className="stat-icon-wrapper stat-icon-lime">
            <CheckSquare size={24} />
          </div>
          <div className="stat-kpi-info">
            <span className="stat-kpi-value">4 Orders</span>
            <span className="stat-kpi-label">Picking Lists Ready</span>
          </div>
        </Card>

        <Card className="stat-card-kpi">
          <div className="stat-icon-wrapper stat-icon-violet">
            <Layers size={24} />
          </div>
          <div className="stat-kpi-info">
            <span className="stat-kpi-value">Zone South</span>
            <span className="stat-kpi-label">Hub: Electronic City</span>
          </div>
        </Card>
      </div>

      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: '700' }}>Active Materials Stock Catalogue</h3>
          <span style={{ fontSize: '13px', color: 'var(--color-white-dim)' }}>
            Updated live from ERP ledger
          </span>
        </div>

        <div className="solar-table-container">
          <table className="solar-table">
            <thead>
              <tr>
                <th>SKU Code</th>
                <th>Material Description</th>
                <th>Category</th>
                <th>Physical Stock</th>
                <th>Allocated</th>
                <th>Available</th>
                <th>Threshold Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {stock.map((item) => {
                const available = item.in_stock - item.allocated;
                const isLow = available <= item.min_thresh;

                return (
                  <tr key={item.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', color: 'var(--color-lime)' }}>
                      {item.sku}
                    </td>
                    <td style={{ fontWeight: '600', color: 'var(--color-white)' }}>{item.name}</td>
                    <td>
                      <Badge variant="violet">{item.category}</Badge>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: '700' }}>
                      {item.in_stock} {item.unit}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-white-dim)' }}>
                      {item.allocated}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-lime)', fontWeight: '800' }}>
                      {available}
                    </td>
                    <td>
                      {isLow ? (
                        <span className="stock-warning-badge">
                          <AlertTriangle size={14} />
                          <span>Reorder Warning</span>
                        </span>
                      ) : (
                        <Badge variant="success">Healthy</Badge>
                      )}
                    </td>
                    <td>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => showToast(`Picking slip generated for ${item.sku}`)}
                      >
                        Pick
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </AppShell>
  );
}

