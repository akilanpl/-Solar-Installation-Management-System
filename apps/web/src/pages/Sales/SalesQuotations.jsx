import React from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { Badge } from '../../components/Badge/Badge';
import { FileText, Plus, Download, Send } from 'lucide-react';
import './SalesQuotations.css';
import '../Customer/CustomerDashboard.css';

const QUOTES = [
  { id: 'QUO-2026-081', customer: 'Arun Kumar', ref: 'ENQ-2026-002', capacity: '3 kW Hybrid', total: '₹3,40,000', status: 'sent', date: '28 Oct 2026' },
  { id: 'QUO-2026-079', customer: 'TechSpark Innovation Labs', ref: 'ENQ-2026-003', capacity: '10 kW Commercial', total: '₹5,80,000', status: 'approved', date: '26 Oct 2026' },
  { id: 'QUO-2026-074', customer: 'Sunita Deshmukh', ref: 'ENQ-2026-004', capacity: '2 kW Off-grid', total: '₹2,10,000', status: 'draft', date: '25 Oct 2026' },
];

export function SalesQuotations() {
  return (
    <AppShell requiredRole="sales">
      <PageHeader
        title="Engineering Proposals & Sales Quotations"
        description="Generate formal system architecture proposals with bill of materials, warranties, and ROI forecasts."
        action={
          <Button variant="primary" icon={<Plus size={16} />}>
            Create New Proposal
          </Button>
        }
      />

      <Card>
        <div className="solar-table-container">
          <table className="solar-table">
            <thead>
              <tr>
                <th>Quote Reference</th>
                <th>Client Name</th>
                <th>Linked Enquiry</th>
                <th>System Capacity</th>
                <th>Total Value</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {QUOTES.map((q) => (
                <tr key={q.id}>
                  <td style={{ fontWeight: '700', color: 'var(--color-lime)', fontFamily: 'var(--font-mono)' }}>
                    {q.id}
                  </td>
                  <td style={{ fontWeight: '600', color: 'var(--color-white)' }}>{q.customer}</td>
                  <td>{q.ref}</td>
                  <td>{q.capacity}</td>
                  <td style={{ fontWeight: '700' }}>{q.total}</td>
                  <td>
                    <Badge variant={q.status === 'approved' ? 'success' : q.status === 'sent' ? 'violet' : 'neutral'}>
                      {q.status.toUpperCase()}
                    </Badge>
                  </td>
                  <td>{q.date}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <Button size="sm" variant="outline" icon={<Download size={12} />}>
                        PDF
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </AppShell>
  );
}

