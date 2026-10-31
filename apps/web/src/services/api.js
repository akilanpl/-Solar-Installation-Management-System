// SolarOps Resilient Client API Service
// Connects to FastAPI backend (/api/v1) and falls back to persistent local storage mock store

import {
  FAKE_USERS,
  INITIAL_ENQUIRIES,
  INITIAL_STOCK,
  INITIAL_TECHNICIAN_JOBS,
  INITIAL_EMPLOYEES,
  INITIAL_SUPPORT_TICKETS,
} from './mockData';

// Local storage keys
const KEY_ENQUIRIES = 'solarops_enquiries';
const KEY_USER = 'solarops_current_user';
const KEY_STOCK = 'solarops_stock';
const KEY_JOBS = 'solarops_tech_jobs';
const KEY_EMPLOYEES = 'solarops_employees';
const KEY_TICKETS = 'solarops_tickets';

function getStored(key, fallback) {
  try {
    const val = localStorage.getItem(key);
    return val ? JSON.parse(val) : fallback;
  } catch (e) {
    return fallback;
  }
}

function setStored(key, val) {
  try {
    localStorage.setItem(key, JSON.stringify(val));
  } catch (e) {
    console.error('Failed to persist to localStorage', e);
  }
}

// Initialize seed data if not present
if (!localStorage.getItem(KEY_ENQUIRIES)) {
  setStored(KEY_ENQUIRIES, INITIAL_ENQUIRIES);
}
if (!localStorage.getItem(KEY_STOCK)) {
  setStored(KEY_STOCK, INITIAL_STOCK);
}
if (!localStorage.getItem(KEY_JOBS)) {
  setStored(KEY_JOBS, INITIAL_TECHNICIAN_JOBS);
}
if (!localStorage.getItem(KEY_EMPLOYEES)) {
  setStored(KEY_EMPLOYEES, INITIAL_EMPLOYEES);
}
if (!localStorage.getItem(KEY_TICKETS)) {
  setStored(KEY_TICKETS, INITIAL_SUPPORT_TICKETS);
}

export class ApiError extends Error {
  constructor(message, status = 500, code = 'unknown_error') {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

// Safe UUID generator
export function generateUUID() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Fast fetch helper with quick timeout (180ms) to prevent low-network hangs on 3G when backend is offline
async function fastFetch(url, options = {}, timeoutMs = 180) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(timer);
    return res;
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

// Core API client
export const api = {
  // Check active user
  async getMe() {
    // 1. Check local session
    const localUser = getStored(KEY_USER, null);
    if (localUser) {
      return { user: localUser };
    }

    // 2. Try backend with fast timeout
    try {
      const res = await fastFetch('/api/v1/auth/me', { credentials: 'include' });
      if (res.ok) {
        const body = await res.json();
        setStored(KEY_USER, body.user);
        return body;
      }
    } catch (err) {
      // Backend not running or timeout; fallback to default demo user
    }

    const defaultDemoUser = FAKE_USERS.admin;
    setStored(KEY_USER, defaultDemoUser);
    return { user: defaultDemoUser };
  },

  // Direct 1-Click Fake Login Bypass
  bypassLogin(roleKey) {
    const user = FAKE_USERS[roleKey] || FAKE_USERS.customer;
    setStored(KEY_USER, user);
    return user;
  },

  // Standard Login
  async login(identifier, password, accountKind = 'customer') {
    // Try backend first
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          account_kind: accountKind,
          identifier,
          password,
        }),
      });

      if (res.ok) {
        const body = await res.json();
        setStored(KEY_USER, body.user);
        return body;
      }
    } catch (err) {
      // Backend unavailable; continue to mock fallback
    }

    // Mock fallback: Match by email or employee code, or match demo shortcuts
    const id = identifier.trim().toLowerCase();
    let matchedRole = 'customer';

    if (id.includes('sales') || id === 'emp-sales-001') matchedRole = 'sales';
    else if (id.includes('tech') || id === 'emp-tech-001') matchedRole = 'technician';
    else if (id.includes('wh') || id === 'emp-wh-001' || id.includes('ware')) matchedRole = 'warehouse';
    else if (id.includes('sup') || id === 'emp-sup-001') matchedRole = 'support';
    else if (id.includes('adm') || id === 'emp-adm-001' || id.includes('admin')) matchedRole = 'admin';

    const user = { ...FAKE_USERS[matchedRole], email: id.includes('@') ? id : FAKE_USERS[matchedRole].email };
    setStored(KEY_USER, user);
    return { user };
  },

  // Signup
  async signup(data) {
    try {
      const res = await fetch('/api/v1/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (err) {
      // Fallback
    }
    // Mock user created
    const newUser = {
      id: 'usr_' + generateUUID().slice(0, 8),
      full_name: data.full_name,
      email: data.email,
      role: 'customer',
      employee_code: null,
      phone: data.phone || '',
      address: data.address || '',
    };
    return { status: 'created', user: newUser, verification_required: true };
  },

  // Verify Email
  async verifyEmail(email, code) {
    try {
      const res = await fetch('/api/v1/auth/verify-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code }),
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (err) {}
    // Bypass verification on mock
    return { verified: true };
  },

  // Dev Mailbox OTP code helper
  async getDevMailboxCode(email) {
    try {
      const res = await fetch(`/api/v1/dev/mailbox/${encodeURIComponent(email)}`);
      if (res.ok) {
        const data = await res.json();
        return data.code;
      }
    } catch (err) {}
    return '123456'; // Default fallback OTP
  },

  // Logout
  async logout() {
    try {
      await fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'include' });
    } catch (err) {}
    localStorage.removeItem(KEY_USER);
    return { ok: true };
  },

  // Get enquiries list
  async getEnquiries() {
    try {
      const res = await fastFetch('/api/v1/enquiries', { credentials: 'include' });
      if (res.ok) {
        return await res.json();
      }
    } catch (err) {}

    // Mock storage
    const items = getStored(KEY_ENQUIRIES, INITIAL_ENQUIRIES);
    return {
      items,
      total: items.length,
      page: 1,
      page_size: 50,
    };
  },

  // Get single enquiry by ID
  async getEnquiry(id) {
    try {
      const res = await fastFetch(`/api/v1/enquiries/${id}`, { credentials: 'include' });
      if (res.ok) {
        return await res.json();
      }
    } catch (err) {}

    const items = getStored(KEY_ENQUIRIES, INITIAL_ENQUIRIES);
    const item = items.find((e) => e.id === id || e.reference === id);
    if (item) return item;
    throw new ApiError('Enquiry not found', 404, 'not_found');
  },

  // Create new enquiry
  async createEnquiry(payload) {
    const idempotencyKey = generateUUID();
    try {
      const res = await fetch('/api/v1/enquiries', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': idempotencyKey,
        },
        credentials: 'include',
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (err) {}

    // Mock storage insertion
    const items = getStored(KEY_ENQUIRIES, INITIAL_ENQUIRIES);
    const currentUser = getStored(KEY_USER, FAKE_USERS.customer);
    const newRef = `ENQ-2026-${String(items.length + 1).padStart(3, '0')}`;
    const newEnquiry = {
      id: 'enq_' + generateUUID().slice(0, 8),
      reference: newRef,
      customer_id: currentUser?.id || 'usr_cust_001',
      customer_name: currentUser?.full_name || 'Customer',
      customer_email: currentUser?.email || 'customer@solarops.dev',
      customer_phone: payload.contact_phone || currentUser?.phone || '+91 98765 43210',
      status: 'submitted',
      preferred_capacity_w: Number(payload.preferred_capacity_w) || 5000,
      monthly_bill_minor: (Number(payload.monthly_bill_rupees) || 5000) * 100,
      grid_preference: payload.grid_preference || 'on_grid',
      installation_address_line1: payload.installation_address_line1 || 'Site Address',
      installation_address_line2: payload.installation_address_line2 || '',
      city: payload.city || 'Bengaluru',
      state: payload.state || 'Karnataka',
      postal_code: payload.postal_code || '560001',
      roof_type: payload.roof_type || 'Concrete Flat',
      roof_area_sqft: Number(payload.roof_area_sqft) || 800,
      customer_notes: payload.notes || '',
      created_at: new Date().toISOString(),
      qualification_notes: '',
      qualifier_name: null,
      timeline: [
        {
          step: 'Enquiry Received',
          time: new Date().toISOString(),
          detail: 'Submitted via customer portal',
        },
      ],
    };

    items.unshift(newEnquiry);
    setStored(KEY_ENQUIRIES, items);
    return newEnquiry;
  },

  // Update enquiry qualification (Sales action)
  async updateEnquiryQualification(id, { status, qualification_notes, next_action }) {
    try {
      const res = await fetch(`/api/v1/enquiries/${id}/qualification`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ status, qualification_notes }),
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (err) {}

    const items = getStored(KEY_ENQUIRIES, INITIAL_ENQUIRIES);
    const idx = items.findIndex((e) => e.id === id || e.reference === id);
    if (idx !== -1) {
      const currentUser = getStored(KEY_USER, FAKE_USERS.sales);
      items[idx].status = status;
      items[idx].qualification_notes = qualification_notes;
      items[idx].qualifier_name = currentUser?.full_name || 'Priya Sharma (Sales)';
      items[idx].timeline.push({
        step: status === 'qualified' ? 'Qualified' : status === 'disqualified' ? 'Disqualified' : 'Updated',
        time: new Date().toISOString(),
        detail: qualification_notes || (next_action ? `Next: ${next_action}` : 'Updated by sales team'),
      });
      setStored(KEY_ENQUIRIES, items);
      return items[idx];
    }
    throw new ApiError('Enquiry not found', 404, 'not_found');
  },

  // Employees
  async getEmployees() {
    return getStored(KEY_EMPLOYEES, INITIAL_EMPLOYEES);
  },

  async createEmployee(emp) {
    const list = getStored(KEY_EMPLOYEES, INITIAL_EMPLOYEES);
    const newEmp = {
      id: 'emp_' + generateUUID().slice(0, 8),
      employee_code: `EMP-${emp.role.slice(0, 3).toUpperCase()}-${String(list.length + 1).padStart(3, '0')}`,
      status: 'active',
      joined: new Date().toISOString().slice(0, 10),
      ...emp,
    };
    list.push(newEmp);
    setStored(KEY_EMPLOYEES, list);
    return newEmp;
  },

  // Stock
  async getStock() {
    return getStored(KEY_STOCK, INITIAL_STOCK);
  },

  // Technician Jobs
  async getTechnicianJobs() {
    return getStored(KEY_JOBS, INITIAL_TECHNICIAN_JOBS);
  },

  async toggleJobChecklistItem(jobId, checkId) {
    const list = getStored(KEY_JOBS, INITIAL_TECHNICIAN_JOBS);
    const job = list.find((j) => j.id === jobId);
    if (job) {
      const item = job.checklist.find((c) => c.id === checkId);
      if (item) item.done = !item.done;
      setStored(KEY_JOBS, list);
    }
    return list;
  },

  // Support Tickets
  async getSupportTickets() {
    return getStored(KEY_TICKETS, INITIAL_SUPPORT_TICKETS);
  },
};

