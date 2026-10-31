"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Button, Card, ErrorState, SelectField, TextField } from "@/components/ui";
import { api, ApiError, type CurrentUser } from "@/lib/api";
import { destinationAfterLogin, isRole } from "@/lib/access";

const PORTALS = [
  { value: "customer", label: "Customer" },
  { value: "technician", label: "Technician" },
  { value: "sales", label: "Sales" },
  { value: "warehouse", label: "Warehouse" },
  { value: "support", label: "Support" },
  { value: "admin", label: "Admin" },
];

function LoginForm() {
  const params = useSearchParams();
  const [portal, setPortal] = useState("customer");
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const verified = params.get("verified") === "1";

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    const form = new FormData(event.currentTarget);
    const identifier = String(form.get("identifier") ?? "").trim();
    const password = String(form.get("password") ?? "");
    const accountKind = portal === "customer" ? "customer" : "employee";
    setPending(true);
    try {
      const body = await api<{ user: CurrentUser }>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({
          account_kind: accountKind,
          identifier,
          password,
        }),
      });
      if (!isRole(body.user.role)) {
        setFormError("This account has an unknown role.");
        return;
      }
      const next = destinationAfterLogin(body.user.role, params.get("next"));
      if (portal !== "customer" && !next.startsWith(`/${portal}`) && body.user.role !== "admin") {
        window.location.assign(`${next}?portal=ignored`);
        return;
      }
      window.location.assign(next);
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "email_not_verified") {
        window.location.assign(`/verify-email?email=${encodeURIComponent(identifier)}`);
        return;
      }
      setFormError(caught instanceof ApiError ? caught.message : "Sign-in failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md items-center px-4 py-10">
      <Card className="w-full">
        <p className="text-xs font-semibold uppercase tracking-wide text-moss-700">SunPower Solutions</p>
        <h1 className="mt-1 text-2xl font-semibold">Sign in to SolarOps</h1>
        <p className="mt-2 text-sm text-moss-900/80">
          The menu chooses the sign-in form. It does not grant a role. Your account record decides what you can open.
        </p>
        {verified ? <p className="mt-3 text-sm text-moss-800">Email verified. You can sign in.</p> : null}
        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <SelectField
            label="I am signing in as"
            name="portal"
            value={portal}
            onChange={(event) => setPortal(event.target.value)}
          >
            {PORTALS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </SelectField>
          <TextField
            label={portal === "customer" ? "Email" : "Employee ID"}
            name="identifier"
            autoComplete={portal === "customer" ? "email" : "username"}
            required
            hint={portal === "customer" ? undefined : "Example: EMP-SALES-001"}
          />
          <TextField label="Password" name="password" type="password" autoComplete="current-password" required />
          {formError ? <ErrorState message={formError} /> : null}
          <Button type="submit" disabled={pending} className="w-full">
            {pending ? "Signing in…" : "Sign in"}
          </Button>
        </form>
        <p className="mt-4 text-sm">
          New customer?{" "}
          <Link className="font-semibold text-moss-800 underline" href="/signup">
            Create an account
          </Link>
        </p>
      </Card>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
