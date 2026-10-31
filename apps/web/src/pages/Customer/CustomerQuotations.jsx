import React, { useState } from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { Badge } from '../../components/Badge/Badge';
import { useAuth } from '../../context/AuthContext';
import { Check, Zap, Sparkles, FileDown, ShieldCheck } from 'lucide-react';
import './CustomerQuotations.css';

const PACKAGES = [
  {
    id: 'pkg-3kw',
    name: '3 kW Residential Starter',
    desc: 'Ideal for 2BHK apartments or independent homes with 300-350 units monthly load.',
    price: '₹1,95,000',
    subsidy: 'Eligible for ₹78,000 Govt. PM Surya Ghar Subsidy',
    netEffective: '₹1,17,000 net after subsidy',
    popular: false,
    features: [
      '6x 540W Mono-PERC Bifacial Modules (Tier-1)',
      '1x 3.3kW Single-Phase Grid Tie Inverter',
      'Hot-dip galvanized anodized roof mounting structure',
      'Dual Type-2 Surge Protection Devices (ACDB/DCDB)',
      'DISCOM Net Metering Liaison & Liaisoning',
      '25-Year Linear Power Performance Warranty',
    ],
  },
  {
    id: 'pkg-5kw',
    name: '5 kW Performance Hybrid',
    desc: 'Most popular package for 3BHK-4BHK villas with air conditioning & EV charging.',
    price: '₹3,40,000',
    subsidy: 'Eligible for ₹78,000 Central Govt. Subsidy',
    netEffective: '₹2,62,000 net after subsidy',
    popular: true,
    features: [
      '10x 540W TopCon High-Efficiency Modules (22.8% eff.)',
      '1x 5kW SunPower Hybrid Inverter (Dual MPPT)',
      'Ready for 5kWh / 10kWh LiFePO4 battery integration',
      'Zero-export device & real-time mobile app IoT telemetry',
      'Complete end-to-end electrical earthing & lightning arrester',
      '10-Year Comprehensive Inverter In-Home Warranty',
    ],
  },
  {
    id: 'pkg-10kw',
    name: '10 kW Commercial Powerhouse',
    desc: 'Designed for small offices, clinics, and commercial rooftop net metering.',
    price: '₹5,80,000',
    subsidy: '40% Accelerated Depreciation tax benefit available',
    netEffective: 'Accelerated 3.2 year investment payback',
    popular: false,
    features: [
      '19x 540W Industrial Grade Monocrystalline Modules',
      '1x 10kW Three-Phase High Voltage Inverter',
      'Custom elevated structural walkway for easy maintenance',
      'Class-A 4-core copper DC cabling with double insulation',
      'Dedicated CEIG electrical inspectorate statutory approval',
      'Quarterly preventative maintenance visits for 3 years',
    ],
  },
];

export function CustomerQuotations() {
  const { showToast } = useAuth();
  const [selectedPkg, setSelectedPkg] = useState(null);

  const handleSelect = (pkgName) => {
    setSelectedPkg(pkgName);
    showToast(`Quotation requested for ${pkgName}. A technical executive will call you.`);
  };

  return (
    <AppShell requiredRole="customer">
      <PageHeader
        title="Solar Package Quotations & Turnkey Estimates"
        description="Transparent engineering proposals, Tier-1 bill of materials, and direct government subsidy deductions."
      />

      <div className="quotation-cards-grid">
        {PACKAGES.map((pkg) => (
          <div
            key={pkg.id}
            className={`package-card ${pkg.popular ? 'popular' : ''}`}
          >
            {pkg.popular && <span className="popular-badge">  Recommended</span>}
            <h3 className="package-name">{pkg.name}</h3>
            <p className="package-desc">{pkg.desc}</p>

            <div className="package-price-box">
              <span className="package-price">{pkg.price}</span>
              <p className="package-subsidy">{pkg.subsidy}</p>
              <p style={{ fontSize: '11px', color: 'var(--color-white-dim)', marginTop: '2px' }}>
                {pkg.netEffective}
              </p>
            </div>

            <div className="feature-list">
              {pkg.features.map((f, idx) => (
                <div key={idx} className="feature-item">
                  <Check size={16} color="var(--color-lime)" style={{ flexShrink: 0 }} />
                  <span>{f}</span>
                </div>
              ))}
            </div>

            <Button
              variant={pkg.popular ? 'primary' : 'outline'}
              fullWidth
              onClick={() => handleSelect(pkg.name)}
            >
              {selectedPkg === pkg.name ? 'Proposal Requested ✓' : 'Select Package'}
            </Button>
          </div>
        ))}
      </div>
    </AppShell>
  );
}

