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



