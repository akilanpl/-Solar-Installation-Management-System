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
