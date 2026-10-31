export const GRID_LABEL = {
  on_grid: 'On-grid',
  off_grid: 'Off-grid',
  hybrid: 'Hybrid',
};

export const STATUS_META = {
  submitted: { label: 'Submitted', variant: 'info' },
  under_review: { label: 'Under Review', variant: 'warning' },
  clarification_requested: { label: 'Clarification Needed', variant: 'warning' },
  qualified: { label: 'Qualified', variant: 'success' },
  disqualified: { label: 'Disqualified', variant: 'danger' },
  survey_scheduled: { label: 'Survey Scheduled', variant: 'violet' },
  in_progress: { label: 'In Progress', variant: 'info' },
  completed: { label: 'Completed', variant: 'success' },
};

export function formatCapacity(watts) {
  if (watts == null) return '—';
  if (watts >= 1000) {
    const kw = watts / 1000;
    return `${kw % 1 === 0 ? kw : kw.toFixed(1)} kW`;
  }
  return `${watts} W`;
}

export function formatInrFromPaise(paise) {
  if (paise == null) return '—';
  const rupees = paise / 100;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(rupees);
}

export function formatWhen(iso) {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export function formatDateTime(iso) {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

