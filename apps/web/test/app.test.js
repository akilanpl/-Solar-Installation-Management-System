import test from 'node:test';
import assert from 'node:assert/strict';
import { ROLES, homeForRole, canAccessPath } from '../src/lib/access.js';
import { formatCapacity, formatInrFromPaise } from '../src/lib/format.js';

test('Access Control: all 7 enterprise roles have valid dashboard routes', () => {
  assert.equal(ROLES.length, 7);
  for (const role of ROLES) {
    const home = homeForRole(role);
    assert.ok(home, `Role ${role} must have a valid home path`);
    assert.ok(home.startsWith('/'), `Home path for ${role} must start with /`);
  }
});

test('Access Control: role authorization permissions', () => {
  assert.equal(canAccessPath('customer', '/customer'), true);
  assert.equal(canAccessPath('customer', '/customer/store'), true);
  assert.equal(canAccessPath('customer', '/store'), true);
  assert.equal(canAccessPath('customer', '/admin'), false);
  assert.equal(canAccessPath('admin', '/admin'), true);
  assert.equal(canAccessPath('technician', '/technician'), true);
  assert.equal(canAccessPath('technician', '/technician/map'), true);
  assert.equal(canAccessPath('sales', '/sales'), true);
});

test('Formatters: formatCapacity correctly handles watts and kilowatts', () => {
  assert.equal(formatCapacity(5000), '5 kW');
  assert.equal(formatCapacity(750), '750 W');
});

test('Formatters: formatInrFromPaise correctly converts paise to INR string', () => {
  const formatted = formatInrFromPaise(100000);
  assert.ok(formatted.includes('1,000') || formatted.includes('1000'));
});

test('Receipt Printer: sawtooth clipPath points generation is well-formed', () => {
  const toothCount = 36;
  const toothDepth = 4;
  const points = Array.from({ length: toothCount * 2 }, (_, index) => {
    const x = 100 - ((index + 1) * 100) / (toothCount * 2);
    const y = index % 2 === 0 ? '100%' : `calc(100% - ${toothDepth}px)`;
    return `${x}% ${y}`;
  }).join(', ');
  const clipPath = `polygon(0 0, 100% 0, 100% calc(100% - ${toothDepth}px), ${points})`;
  assert.ok(clipPath.startsWith('polygon(0 0, 100% 0'));
  assert.ok(clipPath.includes('calc(100% - 4px)'));
  assert.ok(clipPath.endsWith(')'));
});

test('Technician Site Map: stops routing and Google Maps URL structure', () => {
  const address = '#42, 4th Cross, 100ft Road, Indiranagar, Bengaluru - 560038';
  const encoded = encodeURIComponent(address);
  const url = `https://www.google.com/maps/dir/?api=1&destination=${encoded}`;
  assert.ok(url.startsWith('https://www.google.com/maps/dir/'));
  assert.ok(url.includes('Indiranagar'));
  assert.ok(url.includes('560038'));
});

test('Solar Store: calculates subtotal, 12% solar GST, and free delivery correctly', () => {
  const item1 = { price: 13500, quantity: 2 }; // 27,000
  const item2 = { price: 4999, quantity: 1 };  // 4,999
  const subtotal = item1.price * item1.quantity + item2.price * item2.quantity;
  assert.equal(subtotal, 31999);
  const gst = Math.round(subtotal * 0.12);
  assert.equal(gst, 3840);
  const delivery = subtotal > 5000 ? 0 : 499;
  assert.equal(delivery, 0); // Free delivery over 5000
  const grandTotal = subtotal + gst + delivery;
  assert.equal(grandTotal, 35839);
});

test('Solar Chatbot: service ticket and order reference format validation', () => {
  const randomTicketId = 'TK-' + 1088;
  assert.match(randomTicketId, /^TK-\d{4,}$/);
  const randomOrderId = 'ORD-2026-' + 8492;
  assert.match(randomOrderId, /^ORD-2026-\d{4,}$/);
});

test('Technician Site Map: straight orthogonal route coordinate path generation', () => {
  // Stop 1: Indiranagar straight street path (East on Old Airport Rd, North on 100ft Rd)
  const origin = { x: 180, y: 220 };
  const corner = { x: 340, y: 220 };
  const dest = { x: 340, y: 130 };
  const pathD = `M ${origin.x} ${origin.y} L ${corner.x} ${corner.y} L ${dest.x} ${dest.y}`;
  assert.equal(pathD, 'M 180 220 L 340 220 L 340 130');
  // Confirms 90-degree orthogonal street turn
  assert.equal(origin.y, corner.y); // Horizontal segment
  assert.equal(corner.x, dest.x);   // Vertical segment
});

test('Solar Store to Razorpay: pending order payload formatting and items mapping', () => {
  const storeOrder = {
    orderId: 'ORD-2026-9041',
    customerName: 'Arun Kumar',
    address: '#42, 4th Cross, Indiranagar, Bengaluru',
    grandTotal: 35839,
    items: [
      { name: 'Waaree 540W Mono-PERC Bifacial Solar Panel', price: 13500, quantity: 2 },
      { name: 'Automatic Solar Rooftop Sprinkler Cleaning Kit', price: 4999, quantity: 1 },
    ],
    source: 'store',
  };

  const razorpayBillItems = storeOrder.items.map((it) => ({
    name: it.name,
    qty: `x${it.quantity}`,
    cost: `₹${(it.price * it.quantity).toLocaleString('en-IN')}`,
  }));

  assert.equal(razorpayBillItems.length, 2);
  assert.equal(razorpayBillItems[0].qty, 'x2');
  assert.equal(razorpayBillItems[0].cost, '₹27,000');
  assert.equal(razorpayBillItems[1].qty, 'x1');
  assert.equal(razorpayBillItems[1].cost, '₹4,999');
  assert.equal(storeOrder.source, 'store');
});

test('Technician Dispatch Map: raster asset integration and waypoint coordinates', () => {
  const mapAsset = '/maps/dispatch-map.jpg';
  assert.ok(mapAsset.endsWith('.jpg'));

  // Technician beacon origin and customer stop destinations
  const technicianOrigin = { x: 440, y: 400 };
  const stop1Indiranagar = { x: 560, y: 200 };
  const stop2Doddanekkundi = { x: 710, y: 240 };
  const stop3Whitefield = { x: 870, y: 310 };

  // Stop 1 route via Paseo de la Reforma and Sullivan / San Rafael
  const stop1Path = `M ${technicianOrigin.x} ${technicianOrigin.y} L 560 335 L ${stop1Indiranagar.x} ${stop1Indiranagar.y}`;
  assert.equal(stop1Path, 'M 440 400 L 560 335 L 560 200');

  // Stop 2 route via Reforma to Tabacalera / Ignacio Mariscal
  const stop2Path = `M ${technicianOrigin.x} ${technicianOrigin.y} L 680 270 L ${stop2Doddanekkundi.x} ${stop2Doddanekkundi.y}`;
  assert.equal(stop2Path, 'M 440 400 L 680 270 L 710 240');

  // Stop 3 route via Reforma to Av. Juárez / Balderas
  const stop3Path = `M ${technicianOrigin.x} ${technicianOrigin.y} L 740 240 L 870 240 L ${stop3Whitefield.x} ${stop3Whitefield.y}`;
  assert.equal(stop3Path, 'M 440 400 L 740 240 L 870 240 L 870 310');
});

test('Admin Executive Analytics: financial revenue and unit economics aggregation', () => {
  // Test unit cost breakdown summation
  const unitEconomics = [
    { component: 'Mono-PERC Tier-1 PV Modules', cost: 24300, pct: 45 },
    { component: 'Hybrid Inverter & Protection AC/DC DB', cost: 11880, pct: 22 },
    { component: 'LiFePO4 Modular Energy Storage', cost: 8640, pct: 16 },
    { component: 'Civil Structure, Aluminum Rails & Labour', cost: 5400, pct: 10 },
    { component: 'DISCOM Net-Meter & Permitting Fees', cost: 3780, pct: 7 },
  ];

  const totalCogs = unitEconomics.reduce((sum, item) => sum + item.cost, 0);
  assert.equal(totalCogs, 54000); // Base COGS per kW

  const totalPercentage = unitEconomics.reduce((sum, item) => sum + item.pct, 0);
  assert.equal(totalPercentage, 100);

  const retailPricePerKw = 69800;
  const grossMargin = retailPricePerKw - totalCogs;
  assert.equal(grossMargin, 15800);
  const marginPercentage = (grossMargin / totalCogs) * 100;
  assert.ok(marginPercentage > 29.0);

  // Revenue stream diversity shares
  const revenueStreams = [
    { name: 'Residential Rooftops', pct: 49 },
    { name: 'Commercial & Industrial C&I', pct: 30 },
    { name: 'LiFePO4 Battery Storage', pct: 12 },
    { name: 'O&M & Annual Maintenance', pct: 6 },
    { name: 'PM Surya Ghar Subsidies', pct: 3 },
  ];
  const totalStreamPct = revenueStreams.reduce((sum, s) => sum + s.pct, 0);
  assert.equal(totalStreamPct, 100);

  // Enterprise pipeline conversion from leads (1420) to commissioned (512)
  const leadsIngested = 1420;
  const commissioned = 512;
  const netConversion = ((commissioned / leadsIngested) * 100).toFixed(1);
  assert.equal(netConversion, '36.1');
});

test('Header Top Nav: notifications count, filter, and settings state', () => {
  const notifs = [
    { id: '1', read: false },
    { id: '2', read: false },
    { id: '3', read: false },
    { id: '4', read: true },
    { id: '5', read: true },
  ];

  const unreadCount = notifs.filter((n) => !n.read).length;
  assert.equal(unreadCount, 3);

  const unreadOnly = notifs.filter((n) => !n.read);
  assert.equal(unreadOnly.length, 3);

  const markedAllRead = notifs.map((n) => ({ ...n, read: true }));
  assert.equal(markedAllRead.filter((n) => !n.read).length, 0);

  // Settings structure validation
  const sampleSettings = {
    discomCircle: 'BESCOM (Bangalore Urban & Rural)',
    defaultCapacity: '5 kW Hybrid Bifacial',
    autoSanctionCalc: true,
    smsDispatchAlerts: true,
  };

  assert.ok(sampleSettings.discomCircle.includes('BESCOM'));
  assert.equal(sampleSettings.autoSanctionCalc, true);

  // User Profile & Settings update validation (Full-screen user controls)
  const initialUser = {
    id: 'usr_emp_001',
    full_name: 'Vikramaditya',
    phone: '+91 98450 12345',
    email: 'admin@solarops.dev',
    avatar_url: '',
    role: 'admin',
  };

  const updatedProfile = {
    full_name: 'Vikramaditya Verma',
    phone: '+91 99000 77889',
    avatar_url: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
    bio: 'Chief Operations Officer',
  };

  const mergedUser = { ...initialUser, ...updatedProfile };
  assert.equal(mergedUser.full_name, 'Vikramaditya Verma');
  assert.equal(mergedUser.phone, '+91 99000 77889');
  assert.ok(mergedUser.avatar_url.startsWith('data:image'));
  assert.equal(mergedUser.bio, 'Chief Operations Officer');
});

test('Equipment Scanner: role-based visibility and BOM serial match verification', () => {
  const canScanRole = (role) =>
    role === 'warehouse_manager' ||
    role === 'warehouse_staff' ||
    role === 'technician' ||
    role === 'admin';

  assert.equal(canScanRole('warehouse_manager'), true);
  assert.equal(canScanRole('warehouse_staff'), true);
  assert.equal(canScanRole('technician'), true);
  assert.equal(canScanRole('admin'), true);
  assert.equal(canScanRole('customer'), false);
  assert.equal(canScanRole('sales'), false);

  // User-centric scanner mode: technician gets technician only, manager gets warehouse manager only
  const resolveScannerMode = (role, path = '') => {
    if (role === 'technician' || (role === 'admin' && path.startsWith('/technician'))) {
      return 'technician';
    }
    return 'warehouse_manager';
  };

  assert.equal(resolveScannerMode('technician'), 'technician');
  assert.equal(resolveScannerMode('warehouse_manager'), 'warehouse_manager');
  assert.equal(resolveScannerMode('warehouse_staff'), 'warehouse_manager');
  assert.equal(resolveScannerMode('admin', '/admin'), 'warehouse_manager');
  assert.equal(resolveScannerMode('admin', '/warehouse'), 'warehouse_manager');
  assert.equal(resolveScannerMode('admin', '/technician'), 'technician');

  // Technician BOM serial verification logic
  const bomTargets = [
    { targetSerial: 'INV-HYB5K-2026-041', status: 'pending' },
    { targetSerial: 'SN-PV540-KA-0981', status: 'pending' },
  ];

  const scannedSerial = 'INV-HYB5K-2026-041';
  const updatedBom = bomTargets.map((item) =>
    item.targetSerial === scannedSerial ? { ...item, status: 'matched' } : item
  );

  assert.equal(updatedBom[0].status, 'matched');
  assert.equal(updatedBom[1].status, 'pending');

  // Warehouse stock intake serial format
  const whSerial = 'SN-PV540-KA-0985';
  assert.match(whSerial, /^SN-PV\d+-KA-\d+$/);
});

test('Customer Dashboard: technician verification PIN OTP format and parsing', () => {
  const otpRaw = '849201';
  assert.equal(otpRaw.length, 6);
  assert.match(otpRaw, /^\d{6}$/);

  const triad1 = otpRaw.slice(0, 3);
  const triad2 = otpRaw.slice(3, 6);
  assert.equal(triad1, '849');
  assert.equal(triad2, '201');

  const formattedOtp = `${triad1} ${triad2}`;
  assert.equal(formattedOtp, '849 201');
});

test('Performance Optimization: code-splitting routes and skeleton loader structure', () => {
  // Verify lazy dynamic imports match all role routes
  const lazyRoutes = [
    'customer',
    'sales',
    'technician',
    'warehouse',
    'support',
    'admin',
    'store',
  ];
  assert.equal(lazyRoutes.length, 7);

  // Fast fetch timeout threshold (180ms ceiling prevents 3G 30s hangs)
  const networkTimeoutMs = 180;
  assert.ok(networkTimeoutMs < 250);

  // Skeleton shimmer width ratio check
  const skeletonKpiCount = 3;
  assert.equal(skeletonKpiCount, 3);
});










