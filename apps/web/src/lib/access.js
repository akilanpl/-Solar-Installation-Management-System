export const ROLES = [
  'customer',
  'technician',
  'sales',
  'warehouse_staff',
  'warehouse_manager',
  'support',
  'admin',
];

export const ROLE_HOMES = {
  customer: '/customer',
  technician: '/technician',
  sales: '/sales',
  warehouse_staff: '/warehouse',
  warehouse_manager: '/warehouse',
  support: '/support',
  admin: '/admin',
};

export const ROLE_DISPLAY = {
  customer: 'Customer',
  technician: 'Field Technician',
  sales: 'Sales Executive',
  warehouse_staff: 'Warehouse Staff',
  warehouse_manager: 'Warehouse Manager',
  support: 'Support Specialist',
  admin: 'System Administrator',
};

export function isRole(val) {
  return typeof val === 'string' && ROLES.includes(val);
}

export function homeForRole(role) {
  return ROLE_HOMES[role] || '/login';
}

export function destinationAfterLogin(role, next) {
  if (next && next.startsWith('/') && !next.startsWith('//')) {
    return next;
  }
  return homeForRole(role);
}

export function canAccessPath(role, path) {
  if (role === 'admin') return true;
  if (!role) return false;
  if (path.startsWith('/customer') && role === 'customer') return true;
  if (path.startsWith('/sales') && (role === 'sales' || role === 'admin')) return true;
  if (path.startsWith('/technician') && (role === 'technician' || role === 'admin')) return true;
  if (path.startsWith('/warehouse') && (role.startsWith('warehouse') || role === 'admin')) return true;
  if (path.startsWith('/support') && (role === 'support' || role === 'admin')) return true;
  if (path.startsWith('/admin') && role === 'admin') return true;
  return false;
}

