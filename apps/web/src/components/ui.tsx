import type { ComponentProps } from "react";

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ComponentProps<"button"> & { variant?: "primary" | "secondary" | "danger" | "ghost" }) {
  const styles = {
    primary: "bg-moss-700 text-white hover:bg-moss-800",
    secondary: "bg-white text-ink border border-moss-200 hover:bg-moss-50",
    danger: "bg-clay-700 text-white hover:bg-red-800",
    ghost: "bg-transparent text-moss-800 hover:bg-moss-100",
  }[variant];
  return (
    <button
      className={`inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
      {...props}
    />
  );
}

export function TextField({
  label,
  error,
  hint,
  id,
  ...props
}: ComponentProps<"input"> & { label: string; error?: string; hint?: string }) {
  const fieldId = id ?? props.name;
  return (
    <label className="block text-sm" htmlFor={fieldId}>
      <span className="font-medium text-ink">{label}</span>
      <input
        id={fieldId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${fieldId}-error` : hint ? `${fieldId}-hint` : undefined}
        className="mt-1 w-full rounded-md border border-moss-200 bg-white px-3 py-2 text-ink shadow-sm"
        {...props}
      />
      {hint && !error ? (
        <span id={`${fieldId}-hint`} className="mt-1 block text-xs text-moss-800/80">
          {hint}
        </span>
      ) : null}
      {error ? (
        <span id={`${fieldId}-error`} className="mt-1 block text-xs text-clay-700">
          {error}
        </span>
      ) : null}
    </label>
  );
}

export function SelectField({
  label,
  error,
  id,
  children,
  ...props
}: ComponentProps<"select"> & { label: string; error?: string }) {
  const fieldId = id ?? props.name;
  return (
    <label className="block text-sm" htmlFor={fieldId}>
      <span className="font-medium text-ink">{label}</span>
      <select
        id={fieldId}
        aria-invalid={error ? true : undefined}
        className="mt-1 w-full rounded-md border border-moss-200 bg-white px-3 py-2"
        {...props}
      >
        {children}
      </select>
      {error ? <span className="mt-1 block text-xs text-clay-700">{error}</span> : null}
    </label>
  );
}

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`rounded-xl bg-white p-5 shadow-card ${className}`}>{children}</section>;
}

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
        {description ? <p className="mt-1 max-w-2xl text-sm text-moss-900/80">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const label =
    status === "under_review"
      ? "Under review"
      : status === "not_qualified"
        ? "Not qualified"
        : status === "qualified"
          ? "Qualified"
          : status === "submitted"
            ? "Submitted"
            : status;
  const tone =
    status === "qualified"
      ? "bg-moss-100 text-moss-800"
      : status === "not_qualified"
        ? "bg-clay-50 text-clay-700"
        : status === "under_review"
          ? "bg-sun-100 text-sun-700"
          : "bg-moss-50 text-ink";
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${tone}`}>{label}</span>;
}

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" className="rounded-xl border border-dashed border-moss-200 bg-white p-8 text-sm text-moss-800">
      {label}…
    </div>
  );
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-moss-200 bg-white p-8">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-2 max-w-xl text-sm text-moss-900/80">{body}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-xl border border-clay-700/20 bg-clay-50 p-6">
      <h2 className="font-semibold text-clay-700">Something went wrong</h2>
      <p className="mt-1 text-sm">{message}</p>
      {onRetry ? (
        <button className="mt-3 text-sm font-semibold text-moss-800 underline" onClick={onRetry} type="button">
          Try again
        </button>
      ) : null}
    </div>
  );
}

export function AccessDenied({ home }: { home: string }) {
  return (
    <div className="mx-auto max-w-lg py-16">
      <Card>
        <h1 className="text-xl font-semibold">Access denied</h1>
        <p className="mt-2 text-sm text-moss-900/80">
          Your account does not include this workspace. The sign-in menu cannot change your role.
        </p>
        <a className="mt-4 inline-block text-sm font-semibold text-moss-800 underline" href={home}>
          Go to your workspace
        </a>
      </Card>
    </div>
  );
}

export function ConfirmDialog({
  title,
  body,
  confirmLabel,
  onConfirm,
  onCancel,
  pending,
}: {
  title: string;
  body: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  pending?: boolean;
}) {
  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-ink/40 p-4 sm:items-center" role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        className="w-full max-w-md rounded-xl bg-white p-5 shadow-card"
      >
        <h2 id="confirm-title" className="text-lg font-semibold">
          {title}
        </h2>
        <p className="mt-2 text-sm text-moss-900/80">{body}</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" type="button" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="button" onClick={onConfirm} disabled={pending}>
            {pending ? "Saving…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
