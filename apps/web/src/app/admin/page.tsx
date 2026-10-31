"use client";

import { useEffect, useState } from "react";

import { Workspace } from "@/components/workspace";
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, SelectField, TextField } from "@/components/ui";
import { api, ApiError, type EmployeeCreate, type EmployeeResponse } from "@/lib/api";

export default function AdminHome() {
  return (
    <Workspace path="/admin">
      {() => <Employees />}
    </Workspace>
  );
}

function Employees() {
  const [rows, setRows] = useState<EmployeeResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function load() {
    api<EmployeeResponse[]>("/api/v1/admin/employees")
      .then(setRows)
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load employees."));
  }

  useEffect(load, []);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload: EmployeeCreate = {
      full_name: String(form.get("full_name")),
      email: String(form.get("email")),
      phone: String(form.get("phone")),
      employee_code: String(form.get("employee_code")),
      role: String(form.get("role")) as EmployeeCreate["role"],
      password: String(form.get("password")),
    };
    setPending(true);
    setError(null);
    try {
      await api("/api/v1/admin/employees", { method: "POST", body: JSON.stringify(payload) });
      event.currentTarget.reset();
      load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The employee was not created.");
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Employees"
        description="Staff accounts come from the database. Revenue, labour, and report figures are not implemented, so this page does not show them."
      />
      {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
      {!rows ? <LoadingState label="Loading employees" /> : null}
      {rows && rows.length === 0 ? <EmptyState title="No employees" body="Provision the first staff account below." /> : null}
      {rows && rows.length > 0 ? (
        <div className="overflow-x-auto rounded-xl bg-white shadow-card">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-moss-100 text-xs uppercase tracking-wide text-moss-800">
              <tr>
                <th className="px-4 py-3">Employee ID</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Email</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-moss-50">
                  <td className="px-4 py-3 font-medium">{row.employee_code}</td>
                  <td className="px-4 py-3">{row.full_name}</td>
                  <td className="px-4 py-3">{row.role.replaceAll("_", " ")}</td>
                  <td className="px-4 py-3">{row.email}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      <Card className="mt-6">
        <h2 className="font-semibold">Provision an employee</h2>
        <p className="mt-1 text-sm text-moss-900/80">
          The new account is marked verified because the company checked identity outside this form. Customers cannot use this action.
        </p>
        <form className="mt-4 grid gap-3 md:grid-cols-2" onSubmit={onSubmit}>
          <TextField label="Full name" name="full_name" required />
          <TextField label="Email" name="email" type="email" required />
          <TextField label="Mobile" name="phone" required />
          <TextField label="Employee ID" name="employee_code" required hint="Example: EMP-SALES-002" />
          <SelectField label="Role" name="role" defaultValue="sales">
            <option value="sales">Sales</option>
            <option value="technician">Technician</option>
            <option value="warehouse_staff">Warehouse staff</option>
            <option value="warehouse_manager">Warehouse manager</option>
            <option value="support">Support</option>
            <option value="admin">Admin</option>
          </SelectField>
          <TextField label="Temporary password" name="password" type="password" required />
          <div className="md:col-span-2">
            <Button type="submit" disabled={pending}>{pending ? "Saving…" : "Create employee"}</Button>
          </div>
        </form>
      </Card>
    </>
  );
}
