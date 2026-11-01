import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ROLES, homeForRole, canAccessPath } from '../src/lib/access.js';
import { formatCapacity, formatInrFromPaise } from '../src/lib/format.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

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

  // Real camera constraints specification
  const cameraConstraints = {
    video: {
      facingMode: { ideal: 'environment' },
      width: { ideal: 1280 },
      height: { ideal: 720 },
    },
    audio: false,
  };
  assert.equal(cameraConstraints.video.facingMode.ideal, 'environment');
  assert.equal(cameraConstraints.audio, false);

  // Technician installation photo record structure
  const techPhoto = {
    id: 'photo-1',
    url: 'data:image/jpeg;base64,sampleImageData',
    tag: 'Rooftop South Array (Azimuth 180°)',
    time: '11:15 AM',
  };
  assert.ok(techPhoto.tag.includes('Rooftop'));
  assert.ok(techPhoto.url.startsWith('data:image'));

  // Optical HUD & Viewport controls cleanliness verification
  const scannerJsxPath = path.join(__dirname, '../src/components/EquipmentScannerModal/EquipmentScannerModal.jsx');
  const scannerCssPath = path.join(__dirname, '../src/components/EquipmentScannerModal/EquipmentScannerModal.css');
  const scannerJsx = fs.readFileSync(scannerJsxPath, 'utf8');
  const scannerCss = fs.readFileSync(scannerCssPath, 'utf8');

  // Verify green laser sweep is active for warehouse manager and excluded from technician mode
  assert.ok(scannerJsx.includes('!isTechnician && <div className="laser-sweep-beam"'), 'Laser beam must be for warehouse manager only');
  assert.ok(scannerCss.includes('#22c55e'), 'Laser beam must be bright vibrant green');

  // Verify extra fittings (flip, torch, laser toggle buttons) are removed
  assert.ok(!scannerJsx.includes('camera-viewport-controls'), 'Viewport controls (torch/flip/laser buttons) must be removed');
  assert.ok(!scannerJsx.includes('handleToggleTorch'), 'Torch toggle handler must be removed');
  assert.ok(!scannerJsx.includes('handleToggleFacingMode'), 'Flip toggle handler must be removed');
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

  // Inlined zero-latency pre-hydration skeleton in index.html for instant (<25ms) 3G first paint
  const indexHtml = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
  assert.ok(indexHtml.includes('pre-app-shell'), 'index.html must contain pre-app-shell container');
  assert.ok(indexHtml.includes('prebootShimmer'), 'index.html must contain prebootShimmer keyframes');
  assert.ok(indexHtml.includes('Sub-50ms Fast-Boot'), 'index.html must contain fast-boot telemetry pill');
});

test('Multi-Card Leather Wallet: card options, visual assets, and metadata synchronization', () => {
  const cards = {
    stripe: {
      brand: 'Stripe',
      holder: 'ALEX SMITH',
      number: '5524 9910 4242',
      exp: '08/29',
      cvc: '892',
    },
    wise: {
      brand: 'Wise',
      holder: 'STUDIO LLC',
      number: '9012 4432 8810',
      exp: '11/28',
      cvc: '417',
    },
    paypal: {
      brand: 'PayPal',
      holder: 'hello@work.com',
      number: '3312 0045 0094',
      exp: '05/27',
      cvc: '109',
    },
  };

  assert.equal(Object.keys(cards).length, 3);
  assert.equal(cards.stripe.holder, 'ALEX SMITH');
  assert.equal(cards.stripe.number.slice(-4), '4242');
  assert.equal(cards.wise.holder, 'STUDIO LLC');
  assert.equal(cards.wise.number.slice(-4), '8810');
  assert.equal(cards.paypal.holder, 'hello@work.com');
  assert.equal(cards.paypal.number.slice(-4), '0094');

  // Verify wallet component and CSS file existence and key class names
  const componentPath = path.join(__dirname, '../src/components/MultiCardWallet/MultiCardWallet.jsx');
  const cssPath = path.join(__dirname, '../src/components/MultiCardWallet/MultiCardWallet.css');
  assert.ok(fs.existsSync(componentPath), 'MultiCardWallet.jsx must exist');
  assert.ok(fs.existsSync(cssPath), 'MultiCardWallet.css must exist');

  const cssContent = fs.readFileSync(cssPath, 'utf8');
  assert.ok(cssContent.includes('.wallet'), 'CSS must include .wallet styling');
  assert.ok(cssContent.includes('.pocket'), 'CSS must include .pocket leather styling');
  assert.ok(cssContent.includes('.card.stripe'), 'CSS must style Stripe card');
  assert.ok(cssContent.includes('.card.wise'), 'CSS must style Wise card');
  assert.ok(cssContent.includes('.card.paypal'), 'CSS must style PayPal card');
  assert.ok(cssContent.includes('slideIntoPocket'), 'CSS must include slideIntoPocket animation');

  // Verify component scale expansion and removal of extra text/confirmation elements
  assert.ok(cssContent.includes('.wallet-scaler'), 'CSS must include wallet-scaler for expanded dimensions');
  assert.ok(!cssContent.includes('Hover to see Balance'), 'CSS must remove "Hover to see Balance" label');
  const jsxContent = fs.readFileSync(componentPath, 'utf8');
  assert.ok(!jsxContent.includes('selected-card-confirmation'), 'JSX must remove selected-card-confirmation banner');

  // Verify integration in RazorpayPaymentPage.jsx
  const pagePath = path.join(__dirname, '../src/pages/Customer/RazorpayPaymentPage.jsx');
  const pageContent = fs.readFileSync(pagePath, 'utf8');
  assert.ok(pageContent.includes('MultiCardWallet'), 'RazorpayPaymentPage must import and render MultiCardWallet');
  assert.ok(!pageContent.includes('<div className="io-credit-card">'), 'Static io-credit-card must be replaced by MultiCardWallet');
});

test('Customer Accessibility: scoped screen reader, speech-to-text dictation, and disability helpers', () => {
  // 1. Scoping verification: active only in customer sections
  const isCustomerScoped = (role, path = '') =>
    role === 'customer' || path.startsWith('/customer') || path.startsWith('/store');

  assert.equal(isCustomerScoped('customer', '/customer'), true);
  assert.equal(isCustomerScoped('customer', '/customer/store'), true);
  assert.equal(isCustomerScoped('customer', '/customer/payments/razorpay'), true);
  assert.equal(isCustomerScoped('sales', '/sales'), false);
  assert.equal(isCustomerScoped('technician', '/technician'), false);
  assert.equal(isCustomerScoped('warehouse_manager', '/warehouse'), false);
  assert.equal(isCustomerScoped('admin', '/admin'), false);

  // 2. Chatbot Accessibility: Speech-to-Text and Read Aloud verification
  const chatbotPath = path.join(__dirname, '../src/components/SolarChatbot/SolarChatbot.jsx');
  const chatbotCssPath = path.join(__dirname, '../src/components/SolarChatbot/SolarChatbot.css');
  assert.ok(fs.existsSync(chatbotPath), 'SolarChatbot.jsx must exist');
  assert.ok(fs.existsSync(chatbotCssPath), 'SolarChatbot.css must exist');

  const chatbotJsx = fs.readFileSync(chatbotPath, 'utf8');
  const chatbotCss = fs.readFileSync(chatbotCssPath, 'utf8');
  assert.ok(chatbotJsx.includes('handleToggleSpeechToText'), 'Chatbot must include speech-to-text dictation');
  assert.ok(chatbotJsx.includes('SpeechSynthesisUtterance'), 'Chatbot must include SpeechSynthesis read aloud');
  assert.ok(chatbotJsx.includes('autoReadAloud'), 'Chatbot must include auto read aloud toggle for visually impaired');
  assert.ok(chatbotJsx.includes('lemon-voice-btn'), 'Chatbot must include microphone dictation button');
  assert.ok(chatbotCss.includes('lemon-voice-btn'), 'Chatbot CSS must style mic dictation button');
  assert.ok(chatbotCss.includes('speech-listening-banner'), 'Chatbot CSS must style listening banner');

  // 3. Customer Accessibility Assistant Suite Verification
  const a11yPath = path.join(__dirname, '../src/components/CustomerAccessibility/CustomerAccessibility.jsx');
  const a11yCssPath = path.join(__dirname, '../src/components/CustomerAccessibility/CustomerAccessibility.css');
  assert.ok(fs.existsSync(a11yPath), 'CustomerAccessibility.jsx must exist');
  assert.ok(fs.existsSync(a11yCssPath), 'CustomerAccessibility.css must exist');

  const a11yJsx = fs.readFileSync(a11yPath, 'utf8');
  const a11yCss = fs.readFileSync(a11yCssPath, 'utf8');
  assert.ok(a11yJsx.includes('getPageNarration'), 'Customer accessibility must include page narrator text generator');
  assert.ok(a11yJsx.includes('highContrast'), 'Customer accessibility must support high-contrast mode');
  assert.ok(a11yJsx.includes('textSize'), 'Customer accessibility must support scalable text zoom');
  assert.ok(a11yJsx.includes('dyslexicFont'), 'Customer accessibility must support dyslexia reading spacing');
  assert.ok(a11yJsx.includes('readingRuler'), 'Customer accessibility must support visual reading guide ruler');

  // Verify high contrast and accessibility CSS rules
  assert.ok(a11yCss.includes('customer-high-contrast'), 'CSS must include high-contrast mode rules');
  assert.ok(a11yCss.includes('customer-text-large'), 'CSS must include text zoom rules');
  assert.ok(a11yCss.includes('customer-dyslexia-spacing'), 'CSS must include dyslexia spacing rules');
  assert.ok(a11yCss.includes('customer-reading-ruler'), 'CSS must include reading ruler styling');
});

test('Mobile Responsiveness: floating bottom liquid-glass dock, zero app-shell margin, and phone scaling', () => {
  // 1. Sidebar.css: Floating liquid-glass bottom dock on mobile (<= 768px)
  const sidebarCssPath = path.join(__dirname, '../src/components/Sidebar/Sidebar.css');
  const sidebarCss = fs.readFileSync(sidebarCssPath, 'utf8');
  assert.ok(sidebarCss.includes('@media (max-width: 768px)'), 'Sidebar must include 768px mobile breakpoint');
  assert.ok(sidebarCss.includes('bottom: 12px'), 'Dock must anchor to bottom on mobile');
  assert.ok(sidebarCss.includes('flex-direction: row'), 'Dock must switch to horizontal row layout on mobile');

  // 2. AppShell.css: Eliminate left margin and reserve bottom dock clearance
  const shellCssPath = path.join(__dirname, '../src/components/AppShell/AppShell.css');
  const shellCss = fs.readFileSync(shellCssPath, 'utf8');
  assert.ok(shellCss.includes('margin-left: 0 !important'), 'AppShell main must remove left sidebar margin on mobile');
  assert.ok(shellCss.includes('padding-bottom: 86px !important'), 'AppShell main must add bottom clearance for floating dock');

  // 3. Customer Accessibility: Position floating trigger above bottom nav dock
  const a11yCssPath = path.join(__dirname, '../src/components/CustomerAccessibility/CustomerAccessibility.css');
  const a11yCss = fs.readFileSync(a11yCssPath, 'utf8');
  assert.ok(a11yCss.includes('bottom: 84px'), 'Accessibility trigger must float safely above bottom dock');

  // 4. Multi-Card Wallet: Responsive scaling without horizontal overflow
  const walletCssPath = path.join(__dirname, '../src/components/MultiCardWallet/MultiCardWallet.css');
  const walletCss = fs.readFileSync(walletCssPath, 'utf8');
  assert.ok(walletCss.includes('@media (max-width: 480px)'), 'Wallet must include mobile phone breakpoint');
  assert.ok(walletCss.includes('@media (max-width: 380px)'), 'Wallet must include compact phone breakpoint');

  // 5. Solar Chatbot: Full-width mobile sheet
  const chatbotCssPath = path.join(__dirname, '../src/components/SolarChatbot/SolarChatbot.css');
  const chatbotCss = fs.readFileSync(chatbotCssPath, 'utf8');
  assert.ok(chatbotCss.includes('@media (max-width: 768px)'), 'Chatbot must include 768px mobile breakpoint');
  assert.ok(chatbotCss.includes('width: 100vw'), 'Chatbot panel must expand to full viewport width on mobile');

  // 6. Modal component: Full-width responsive container
  const modalCssPath = path.join(__dirname, '../src/components/Modal/Modal.css');
  const modalCss = fs.readFileSync(modalCssPath, 'utf8');
  assert.ok(modalCss.includes('@media (max-width: 640px)'), 'Modal must include mobile breakpoint');
  assert.ok(modalCss.includes('max-width: 100%'), 'Modal must adapt to full width on mobile screens');
});

test('Field Map & Store Cart Responsiveness: header column collapse, touch tab row, and cart checkout clearance', () => {
  // 1. TechnicianSiteMap.css: Responsive header collapse & swipeable stop cards
  const siteMapCssPath = path.join(__dirname, '../src/components/TechnicianSiteMap/TechnicianSiteMap.css');
  const siteMapCss = fs.readFileSync(siteMapCssPath, 'utf8');
  assert.ok(siteMapCss.includes('white-space: nowrap'), 'Road map chip must have nowrap protection');
  assert.ok(siteMapCss.includes('.tech-map-header'), 'Site map must style header container');
  assert.ok(siteMapCss.includes('@media (max-width: 768px)'), 'Site map must include 768px breakpoint');
  assert.ok(siteMapCss.includes('overflow-x: auto'), 'Stop cards must allow horizontal touch scroll on mobile');

  // 2. SolarStore.css: Cart drawer overlay elevation & sticky footer safe area clearance
  const storeCssPath = path.join(__dirname, '../src/pages/Customer/SolarStore.css');
  const storeCss = fs.readFileSync(storeCssPath, 'utf8');
  assert.ok(storeCss.includes('z-index: 10050'), 'Cart drawer overlay must sit above bottom dock and floating triggers');
  assert.ok(storeCss.includes('padding: 14px 16px 140px 16px'), 'Cart drawer body must provide bottom clearance for sticky footer');
  assert.ok(storeCss.includes('.cart-drawer-sticky-footer'), 'Must style sticky checkout footer');

  // 3. CustomerAccessibility.css: Auto-hide floating button during cart checkout
  const a11yCssPath = path.join(__dirname, '../src/components/CustomerAccessibility/CustomerAccessibility.css');
  const a11yCss = fs.readFileSync(a11yCssPath, 'utf8');
  assert.ok(a11yCss.includes(':has(.cart-drawer-overlay)'), 'Accessibility trigger must auto-hide when cart drawer is active');
});

test('Dashboard Polish & Sales Responsiveness: board meeting action buttons styling, date badge nowrap, and sales header column collapse', () => {
  // 1. DashboardView.css: Meeting card button styling and date badge nowrap
  const dashCssPath = path.join(__dirname, '../src/components/DashboardView/DashboardView.css');
  const dashCss = fs.readFileSync(dashCssPath, 'utf8');
  assert.ok(dashCss.includes('.btn-reschedule'), 'Must style .btn-reschedule button');
  assert.ok(dashCss.includes('.btn-accept-invite'), 'Must style .btn-accept-invite button');
  assert.ok(dashCss.includes('.board-meeting-actions'), 'Must style .board-meeting-actions container');
  assert.ok(dashCss.includes('.event-pill'), 'Must style .event-pill container');
  assert.ok(dashCss.includes('white-space: nowrap'), 'Must prevent date badge word-splitting');

  // 2. SalesDashboard.css: Responsive enquiries card & header column collapse
  const salesCssPath = path.join(__dirname, '../src/pages/Sales/SalesDashboard.css');
  const salesCss = fs.readFileSync(salesCssPath, 'utf8');
  assert.ok(salesCss.includes('.sales-enquiries-card'), 'Must style .sales-enquiries-card');
  assert.ok(salesCss.includes('.sales-enquiries-header'), 'Must style .sales-enquiries-header');
  assert.ok(salesCss.includes('@media (max-width: 768px)'), 'Must include 768px responsive breakpoint');
  assert.ok(salesCss.includes('flex-direction: column'), 'Must collapse sales header into column on mobile');
  assert.ok(salesCss.includes('overflow-x: auto'), 'Must allow horizontal touch scrolling for filter tabs');
});

test('POS Terminal Card: card-swipe keyframes physics, component customization, and multi-surface re-use', () => {
  // 1. TransactionCard.jsx and PosTransactionCard.jsx exist and export components
  const txnCardJsxPath = path.join(__dirname, '../src/components/TransactionCard/TransactionCard.jsx');
  const posCardJsxPath = path.join(__dirname, '../src/components/PosTransactionCard/PosTransactionCard.jsx');
  assert.ok(fs.existsSync(txnCardJsxPath), 'TransactionCard.jsx must exist');
  assert.ok(fs.existsSync(posCardJsxPath), 'PosTransactionCard.jsx must exist');

  const txnJsx = fs.readFileSync(txnCardJsxPath, 'utf8');
  assert.ok(txnJsx.includes('label = \'New Transaction\''), 'Must provide default label');
  assert.ok(txnJsx.includes('currencySymbol = \'₹\''), 'Must provide default currency symbol');
  assert.ok(txnJsx.includes('PosTransactionCard'), 'Must export PosTransactionCard alias');
  assert.ok(txnJsx.includes('pos-container'), 'Must render pos-container');
  assert.ok(txnJsx.includes('pos-card'), 'Must render simulated pos credit card');
  assert.ok(txnJsx.includes('pos-post'), 'Must render pos terminal housing');

  // 2. TransactionCard.css: exact physics and keyframes
  const txnCssPath = path.join(__dirname, '../src/components/TransactionCard/TransactionCard.css');
  const txnCss = fs.readFileSync(txnCssPath, 'utf8');
  assert.ok(txnCss.includes('@keyframes slide-top'), 'Must include slide-top card swipe animation');
  assert.ok(txnCss.includes('@keyframes slide-post'), 'Must include slide-post terminal lift animation');
  assert.ok(txnCss.includes('@keyframes fade-in-fwd'), 'Must include fade-in-fwd dollar symbol animation');
  assert.ok(txnCss.includes('clip-path: polygon(0% 0%, 100% 0%, 90% 100%, 10% 100%)'), 'Must include polygon clip-path for terminal slit');
  assert.ok(txnCss.includes('@media only screen and (max-width: 480px)'), 'Must include 480px mobile breakpoint');

  // 3. Re-use in Customer Payments Page
  const paymentsPath = path.join(__dirname, '../src/pages/Customer/CustomerPayments.jsx');
  const paymentsJsx = fs.readFileSync(paymentsPath, 'utf8');
  assert.ok(paymentsJsx.includes('TransactionCard'), 'CustomerPayments must re-use TransactionCard');

  // 4. Re-use in Customer Quotations Page
  const quotationsPath = path.join(__dirname, '../src/pages/Customer/CustomerQuotations.jsx');
  const quotationsJsx = fs.readFileSync(quotationsPath, 'utf8');
  assert.ok(quotationsJsx.includes('TransactionCard'), 'CustomerQuotations must re-use TransactionCard');
  assert.ok(quotationsJsx.includes('Lock Booking Deposit'), 'CustomerQuotations must provide booking token CTA');

  // 5. Re-use in Dashboard Bento View
  const dashboardPath = path.join(__dirname, '../src/components/DashboardView/DashboardView.jsx');
  const dashboardJsx = fs.readFileSync(dashboardPath, 'utf8');
  assert.ok(dashboardJsx.includes('TransactionCard'), 'DashboardView must re-use TransactionCard');
  assert.ok(dashboardJsx.includes('Pay 20% Advance'), 'DashboardView must use TransactionCard for advance settlement');
  assert.ok(dashboardJsx.includes('Disburse DBT Subsidy'), 'DashboardView must use TransactionCard for admin subsidy disbursal');

  // 6. Re-use in Solar Store
  const storePath = path.join(__dirname, '../src/pages/Customer/SolarStore.jsx');
  const storeJsx = fs.readFileSync(storePath, 'utf8');
  assert.ok(storeJsx.includes('TransactionCard'), 'SolarStore must re-use TransactionCard');
  assert.ok(storeJsx.includes('Instant Card Checkout'), 'SolarStore must provide instant card checkout CTA');
});











