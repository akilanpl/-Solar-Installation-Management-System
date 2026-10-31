"use client";

import { useCallback, useEffect, useState } from "react";
import { Workspace } from "@/components/workspace";
import {
  Button,
  Card,
  ErrorState,
  LoadingState,
  PageHeader,
  SelectField,
  TextField,
} from "@/components/ui";
import { api, type CurrentUser } from "@/lib/api";
import {
  finance,
  inr,
  type FinanceRecord,
  type FinanceDashboard,
  type FinanceJournal,
} from "@/lib/finance";

type Field = {
  name: string;
  label: string;
  type?: "number" | "date" | "datetime-local" | "list" | "checkbox";
  options?: string[];
  optional?: boolean;
};
type Action = { label: string; path: string; fields: Field[]; roles: string[] };
const field = (
  name: string,
  label: string,
  type?: Field["type"],
  optional = false,
): Field => ({ name, label, type, optional });
const dated = [
  field("posting_date", "Posting date", "date"),
  field("policy_id", "Approved policy ID"),
];
const evidence = field("evidence_id", "Uploaded evidence ID");
const keyed = field("key", "Unique request key");
const actions: Action[] = [
  {
    label: "Open accounting period",
    path: "periods",
    roles: ["admin"],
    fields: [
      field("starts_on", "Start date", "date"),
      field("ends_on", "End date", "date"),
    ],
  },
  {
    label: "Approve accounting policy",
    path: "policies",
    roles: ["admin"],
    fields: [
      keyed,
      field("label", "Policy name"),
      field("approval_reference", "Business approval reference"),
      field("effective_from", "Effective from", "date"),
      field("effective_to", "Effective to", "date"),
      {
        name: "recognition",
        label: "Approved recognition policy",
        options: ["completed_installation_and_approved_service"],
      },
      {
        name: "tax",
        label: "Approved tax policy",
        options: ["preserve_approved_source_snapshot"],
      },
      {
        name: "posting_rules",
        label: "Approved posting rules",
        options: ["invoice_deferred_tax_on_issue_costs_on_approval"],
      },
    ],
  },
  {
    label: "Issue source invoice",
    path: "invoices",
    roles: ["admin"],
    fields: [
      ...dated,
      {
        name: "source_kind",
        label: "Source type",
        options: ["order", "service_invoice"],
      },
      field("source_id", "Accepted order or Phase 4B invoice ID"),
    ],
  },
  {
    label: "Recognize completed work",
    path: "invoices/{invoice_id}/recognize",
    roles: ["admin"],
    fields: [field("invoice_id", "Finance invoice ID"), ...dated, evidence],
  },
  {
    label: "Reconcile verified cash",
    path: "receipts/import",
    roles: ["admin"],
    fields: [
      ...dated,
      field("payment_id", "Verified cash payment ID"),
      field("order_id", "Order ID"),
      field(
        "invoice_id",
        "Finance invoice ID (blank records advance)",
        undefined,
        true,
      ),
    ],
  },
  {
    label: "Allocate customer advance",
    path: "advances/allocate",
    roles: ["admin"],
    fields: [
      ...dated,
      field("receipt_id", "Advance receipt ID"),
      field("invoice_id", "Finance invoice ID"),
      field("amount_minor", "Allocation (paise)", "number"),
      keyed,
    ],
  },
  {
    label: "Adjust approved labour",
    path: "payables/{payable_id}/adjustments",
    roles: ["admin"],
    fields: [
      field("payable_id", "Approved timesheet review ID"),
      ...dated,
      field(
        "delta_minor",
        "Adjustment, positive or negative (paise)",
        "number",
      ),
      field("reason", "Adjustment reason"),
      evidence,
      keyed,
    ],
  },
  {
    label: "Credit invoice",
    path: "invoices/{invoice_id}/credits",
    roles: ["admin"],
    fields: [
      field("invoice_id", "Finance invoice ID"),
      ...dated,
      field(
        "source_credit_id",
        "Phase 4B credit ID for service bills",
        undefined,
        true,
      ),
      field("amount_minor", "Credit total (paise)", "number"),
      field("tax_minor", "Approved tax credit (paise)", "number"),
      field("reason", "Reason"),
      evidence,
      keyed,
    ],
  },
  {
    label: "Approve labour rate",
    path: "labour-rates",
    roles: ["admin"],
    fields: [
      field("technician_id", "Technician ID"),
      field("effective_from", "Effective from", "datetime-local"),
      field("effective_to", "Effective to", "datetime-local"),
      field("hourly_minor", "Hourly pay (paise)", "number"),
      evidence,
      keyed,
    ],
  },
  {
    label: "Submit timesheet",
    path: "timesheets",
    roles: ["technician"],
    fields: [
      {
        name: "job_kind",
        label: "Job type",
        options: ["installation", "repair"],
      },
      field("job_id", "Assigned job ID"),
      field("check_in", "Recorded check-in", "datetime-local"),
      field("check_out", "Recorded check-out", "datetime-local"),
      field("note", "Work notes"),
      keyed,
    ],
  },
  {
    label: "Review timesheet",
    path: "timesheets/{sheet_id}/review",
    roles: ["admin"],
    fields: [
      field("sheet_id", "Timesheet ID"),
      ...dated,
      {
        name: "decision",
        label: "Decision",
        options: ["approved", "rejected"],
      },
      field("approved_minutes", "Approved minutes", "number"),
      field("note", "Manager review"),
      evidence,
    ],
  },
  {
    label: "Record evidenced settlement",
    path: "payables/{payable_id}/settlements",
    roles: ["admin"],
    fields: [
      field("payable_id", "Approved timesheet review ID"),
      ...dated,
      field("amount_minor", "Actual settlement (paise)", "number"),
      evidence,
      field("bank_reference", "Actual bank reference"),
    ],
  },
  {
    label: "Record actual cost",
    path: "costs",
    roles: ["admin"],
    fields: [
      ...dated,
      field("order_id", "Order ID"),
      { name: "kind", label: "Cost type", options: ["material", "expense"] },
      field("ledger_id", "Actual consumed stock ledger ID", undefined, true),
      field("amount_minor", "Evidenced cost (paise)", "number"),
      evidence,
      field("description", "Cost description"),
      keyed,
    ],
  },
  {
    label: "Attest cost completeness",
    path: "completeness",
    roles: ["admin"],
    fields: [
      field("order_id", "Order ID"),
      evidence,
      field("labour_complete", "All labour reviewed", "checkbox"),
      field(
        "expenses_complete",
        "All attributable expenses recorded",
        "checkbox",
      ),
      field("note", "Reconciliation notes"),
      keyed,
    ],
  },
  {
    label: "Record official scheme checklist",
    path: "subsidy-schemes",
    roles: ["admin"],
    fields: [
      keyed,
      field("name", "Official scheme name"),
      field("official_url", "Official source URL"),
      field("version", "Official checklist version"),
      field("effective_from", "Effective from", "date"),
      field("effective_to", "Effective to", "date"),
      field("required_documents", "Document types, comma separated", "list"),
      evidence,
    ],
  },
  {
    label: "Start subsidy application",
    path: "subsidies",
    roles: ["customer"],
    fields: [
      field("order_id", "Your order ID"),
      field("scheme_id", "Approved scheme checklist ID"),
      field("consent_text", "Your consent to use these documents"),
      keyed,
    ],
  },
  {
    label: "Attach subsidy document",
    path: "subsidies/{case_id}/documents",
    roles: ["customer"],
    fields: [
      field("case_id", "Application ID"),
      field("document_type", "Checklist document type"),
      evidence,
      keyed,
    ],
  },
  {
    label: "Review or record official decision",
    path: "subsidies/{case_id}/events",
    roles: ["admin", "sales"],
    fields: [
      field("case_id", "Application ID"),
      {
        name: "action",
        label: "Recorded event",
        options: ["reviewed", "submitted", "approved", "rejected"],
      },
      field("note", "Decision notes"),
      evidence,
      field(
        "external_reference",
        "Review, submission or official decision reference",
      ),
      keyed,
    ],
  },
  {
    label: "Withdraw subsidy consent",
    path: "subsidies/{case_id}/events",
    roles: ["customer"],
    fields: [
      field("case_id", "Application ID"),
      {
        name: "action",
        label: "Consent decision",
        options: ["consent_withdrawn"],
      },
      field("note", "Reason"),
      keyed,
    ],
  },
  {
    label: "Reverse recognition",
    path: "journal/{entry_id}/reverse",
    roles: ["admin"],
    fields: [
      field("entry_id", "Recognition journal entry ID"),
      field("posting_date", "Reversal posting date", "date"),
      field("reason", "Reason"),
      evidence,
    ],
  },
  {
    label: "Close accounting period",
    path: "periods/{period_id}/close",
    roles: ["admin"],
    fields: [
      field("period_id", "Period ID"),
      field("evidence", "Closing reconciliation reference"),
    ],
  },
];

function CommandForm({
  user,
  onSaved,
}: {
  user: CurrentUser;
  onSaved: () => void;
}) {
  const choices = actions.filter((a) => a.roles.includes(user.role));
  const [selected, setSelected] = useState(choices[0]?.label ?? "");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState("");
  const action = choices.find((a) => a.label === selected) ?? choices[0];
  if (!action) return null;
  return (
    <Card>
      <h2 className="text-lg font-semibold">Finance actions</h2>
      <SelectField
        label="Action"
        value={action.label}
        onChange={(e) => {
          setSelected(e.target.value);
          setError("");
          setResult("");
        }}
      >
        {choices.map((a) => (
          <option key={a.label}>{a.label}</option>
        ))}
      </SelectField>
      <form
        key={action.label}
        className="mt-4 grid gap-3 sm:grid-cols-2"
        onSubmit={async (e) => {
          e.preventDefault();
          setPending(true);
          setError("");
          setResult("");
          const data = new FormData(e.currentTarget);
          const body: Record<string, unknown> = {};
          let path = action.path;
          for (const f of action.fields) {
            const raw = data.get(f.name);
            const value = String(raw ?? "");
            if (path.includes(`{${f.name}}`)) {
              path = path.replace(`{${f.name}}`, encodeURIComponent(value));
              continue;
            }
            if (!value && f.optional) continue;
            body[f.name] =
              f.type === "number"
                ? Number(value)
                : f.type === "checkbox"
                  ? raw === "on"
                  : f.type === "datetime-local"
                    ? new Date(value).toISOString()
                    : f.type === "list"
                      ? value
                          .split(",")
                          .map((s) => s.trim())
                          .filter(Boolean)
                      : value;
          }
          try {
            const saved = await api<{ id: string }>(`/api/v1/finance/${path}`, {
              method: "POST",
              body: JSON.stringify(body),
            });
            setResult(`Recorded ${saved.id}`);
            onSaved();
          } catch (err) {
            setError(err instanceof Error ? err.message : "Could not save.");
          } finally {
            setPending(false);
          }
        }}
      >
        {action.fields.map((f) =>
          f.options ? (
            <SelectField key={f.name} name={f.name} label={f.label}>
              {f.options.map((o) => (
                <option key={o}>{o}</option>
              ))}
            </SelectField>
          ) : (
            <TextField
              key={f.name}
              name={f.name}
              label={f.label}
              type={f.type === "list" ? "text" : (f.type ?? "text")}
              required={!f.optional}
              min={
                f.type === "number" && f.name !== "delta_minor" ? 0 : undefined
              }
              step={f.type === "number" ? 1 : undefined}
            />
          ),
        )}
        <div className="sm:col-span-2">
          <Button disabled={pending}>
            {pending ? "Recording…" : action.label}
          </Button>
        </div>
      </form>
      {error ? (
        <div className="mt-3">
          <ErrorState message={error} />
        </div>
      ) : null}
      {result ? (
        <p role="status" className="mt-3 break-all text-sm">
          {result}
        </p>
      ) : null}
      <p className="mt-3 text-xs text-moss-800">
        {user.role === "admin" || user.role === "technician"
          ? "Amounts use INR paise. Approval creates a liability. Only an evidenced settlement records money transferred."
          : "Complete the checklist and record your consent before sales review. Official submissions and decisions require supporting evidence."}
      </p>
    </Card>
  );
}

function EvidenceUpload() {
  const [result, setResult] = useState("");
  const [pending, setPending] = useState(false);
  return (
    <Card>
      <h2 className="font-semibold">Upload supporting evidence</h2>
      <form
        className="mt-3 flex flex-wrap gap-3"
        onSubmit={async (e) => {
          e.preventDefault();
          setPending(true);
          try {
            const body = new FormData(e.currentTarget);
            const saved = await api<{ id: string; sha256: string }>(
              "/api/v1/finance/evidence",
              { method: "POST", body },
            );
            setResult(`Evidence ID: ${saved.id} · SHA-256: ${saved.sha256}`);
          } catch (err) {
            setResult(err instanceof Error ? err.message : "Upload failed.");
          } finally {
            setPending(false);
          }
        }}
      >
        <label className="text-sm">
          PDF or image (up to 5 MB)
          <input
            className="mt-2 block"
            name="file"
            type="file"
            accept="application/pdf,image/jpeg,image/png,image/webp"
            required
          />
        </label>
        <Button disabled={pending}>Upload evidence</Button>
      </form>
      <p role="status" className="mt-3 break-all text-sm">
        {result}
      </p>
    </Card>
  );
}

function FinanceContent({ user }: { user: CurrentUser }) {
  const [rows, setRows] = useState<FinanceRecord[]>([]);
  const [dashboard, setDashboard] = useState<FinanceDashboard | null>(null);
  const [journal, setJournal] = useState<FinanceJournal[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [order, setOrder] = useState("");
  const [detail, setDetail] = useState<FinanceRecord | null>(null);
  const [subsidy, setSubsidy] = useState<{
    state: string;
    missing: string[];
  } | null>(null);
  const load = useCallback(async () => {
    try {
      const [records, report, entries] = await Promise.all([
        finance.records(),
        user.role === "admin" ? finance.dashboard() : null,
        user.role === "admin" ? finance.journal() : [],
      ]);
      setRows(records);
      setDashboard(report);
      setJournal(entries);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load finance.");
    } finally {
      setLoading(false);
    }
  }, [user.role]);
  useEffect(() => {
    void load();
  }, [load]);
  const visible = rows.filter((r) => !order || r.order_id === order);
  return (
    <>
      <PageHeader
        title={
          user.role === "admin"
            ? "Financial operations"
            : user.role === "technician"
              ? "Labour and payables"
              : "Subsidy documents"
        }
        description="Source records, approvals and reconciled financial events."
        action={
          user.role === "admin" ? (
            <a
              className="text-sm underline"
              href="/api/v1/finance/reports/profit.csv"
            >
              Export reconciled CSV
            </a>
          ) : undefined
        }
      />
      {error ? (
        <ErrorState message={error} onRetry={() => void load()} />
      ) : null}
      {loading ? <LoadingState /> : null}
      {dashboard ? (
        <>
          <div className="mb-5 grid gap-3 sm:grid-cols-3">
            {[
              ["Recognized revenue", dashboard.recognized_revenue_minor],
              ["Cash recorded", dashboard.cash_minor],
              ["Receivables", dashboard.receivables_minor],
              ["Payables outstanding", dashboard.payables_minor],
              ["Customer advances", dashboard.advances_minor],
              ["Deferred revenue", dashboard.deferred_revenue_minor],
            ].map(([label, value]) => (
              <Card key={label}>
                <p className="text-sm text-moss-800">{label}</p>
                <p className="mt-2 text-xl font-semibold">
                  {inr(Number(value))}
                </p>
              </Card>
            ))}
          </div>
          <Card>
            <h2 className="font-semibold">Job profitability</h2>
            <p className="my-2 text-sm">
              Outstanding installations: {dashboard.outstanding_jobs}. Service
              liabilities: {dashboard.service_liability_state}.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr>
                    {[
                      "Order",
                      "Revenue",
                      "Material",
                      "Labour",
                      "Expenses",
                      "Profit / loss",
                      "Reconciliation",
                    ].map((h) => (
                      <th className="p-2" key={h}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dashboard.jobs.map((j) => (
                    <tr key={j.order_id} className="border-t border-moss-100">
                      <td className="p-2">
                        <button
                          className="underline"
                          onClick={() => setOrder(j.order_id)}
                        >
                          {j.reference}
                        </button>
                      </td>
                      {[
                        j.revenue_minor,
                        j.material_minor,
                        j.labour_minor,
                        j.expense_minor,
                        j.profit_minor,
                      ].map((v, i) => (
                        <td
                          key={i}
                          className={`p-2 ${v < 0 ? "text-clay-700" : ""}`}
                        >
                          {inr(v)}
                        </td>
                      ))}
                      <td className="p-2">
                        {j.complete
                          ? "Complete"
                          : `Incomplete: ${j.missing.join(", ")}`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!dashboard.jobs.length ? (
              <p className="text-sm">No source orders.</p>
            ) : null}
            <p className="mt-3 text-sm">
              Subsidy status:{" "}
              {Object.entries(dashboard.subsidy_status)
                .map(([k, v]) => `${k}: ${v}`)
                .join(" · ") || "No applications"}
            </p>
          </Card>
        </>
      ) : null}
      <div className="mt-5 grid gap-5">
        <EvidenceUpload />
        <CommandForm user={user} onSaved={() => void load()} />
        <Card>
          <div className="flex justify-between">
            <h2 className="font-semibold">Source records</h2>
            {order ? (
              <Button variant="secondary" onClick={() => setOrder("")}>
                Clear job filter
              </Button>
            ) : null}
          </div>
          <p className="my-2 text-sm">
            Select a record to view its approved details and supporting
            evidence. Approval alone does not confirm a payment.
          </p>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Record</th>
                  <th>Amount / state</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((r) => (
                  <tr key={r.id} className="border-t border-moss-100">
                    <td className="p-2">{r.kind}</td>
                    <td className="p-2">
                      <button
                        className="underline break-all"
                        onClick={async () => {
                          setDetail(r);
                          setSubsidy(null);
                          if (r.kind === "subsidy_case") {
                            try {
                              setSubsidy(
                                await api(`/api/v1/finance/subsidies/${r.id}`),
                              );
                            } catch (err) {
                              setError(String(err));
                            }
                          }
                        }}
                      >
                        {r.id}
                      </button>
                    </td>
                    <td className="p-2">
                      {r.kind === "timesheet_review" &&
                      r.payload.decision === "approved"
                        ? (() => {
                            const adjustments = rows
                              .filter(
                                (a) =>
                                  a.kind === "labour_adjustment" &&
                                  a.payload.payable_id === r.id,
                              )
                              .reduce(
                                (sum, a) => sum + Number(a.payload.delta_minor),
                                0,
                              );
                            const paid = rows
                              .filter(
                                (a) =>
                                  a.kind === "settlement" &&
                                  a.payload.payable_id === r.id,
                              )
                              .reduce(
                                (sum, a) =>
                                  sum + Number(a.payload.amount_minor),
                                0,
                              );
                            const due =
                              Number(r.payload.amount_minor) +
                              adjustments -
                              paid;
                            return `${inr(due)} ${due === 0 ? "settled with evidence" : "unsettled"}`;
                          })()
                        : typeof r.payload.amount_minor === "number"
                          ? inr(r.payload.amount_minor)
                          : typeof r.payload.total_minor === "number"
                            ? inr(r.payload.total_minor)
                            : String(
                                r.payload.action ??
                                  r.payload.decision ??
                                  "Recorded",
                              )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!visible.length ? <p>No finance records available.</p> : null}
          {detail ? (
            <div className="mt-4">
              <h3 className="font-semibold">Record {detail.id}</h3>
              {subsidy ? (
                <p>
                  Application status: {subsidy.state} · Missing documents:{" "}
                  {subsidy.missing.join(", ") || "None"}
                </p>
              ) : null}
              <pre className="mt-2 overflow-auto rounded bg-moss-50 p-3 text-xs">
                {JSON.stringify(detail, null, 2)}
              </pre>
            </div>
          ) : null}
        </Card>
        {user.role === "admin" ? (
          <Card>
            <h2 className="font-semibold">Source-linked journal</h2>
            <div className="max-h-96 overflow-auto">
              {journal
                .filter(
                  (j) => !order || visible.some((r) => r.id === j.record_id),
                )
                .map((j) => (
                  <details key={j.id} className="border-b border-moss-100 py-2">
                    <summary className="cursor-pointer text-sm">
                      {j.posting_date} · {j.source_event}
                    </summary>
                    <pre className="overflow-auto text-xs">
                      {JSON.stringify(j, null, 2)}
                    </pre>
                  </details>
                ))}
            </div>
          </Card>
        ) : null}
      </div>
    </>
  );
}

export function FinanceWorkspace({ path }: { path: string }) {
  return (
    <Workspace path={path}>
      {(user) => <FinanceContent user={user} />}
    </Workspace>
  );
}
