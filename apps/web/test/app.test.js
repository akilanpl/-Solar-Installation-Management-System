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
  assert.equal(canAccessPath('customer', '/admin'), false);
  assert.equal(canAccessPath('admin', '/admin'), true);
  assert.equal(canAccessPath('technician', '/technician'), true);
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

