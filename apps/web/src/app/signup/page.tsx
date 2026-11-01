"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button, Card, ErrorState, TextField } from "@/components/ui";
import { api, ApiError, fieldErrors } from "@/lib/api";

export default function SignupPage() {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  useEffect(() => {
    document.body.dataset.signupReady = "1";
  }, []);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    const form = new FormData(event.currentTarget);
    const fullName = String(form.get("full_name") ?? "").trim();
    const email = String(form.get("email") ?? "").trim();
    const phone = String(form.get("phone") ?? "").trim();
    const password = String(form.get("password") ?? "");
    const nextErrors: Record<string, string> = {};
    if (fullName.length < 2) nextErrors.full_name = "Enter your name.";
    if (!/^[6-9][0-9]{9}$/.test(phone)) nextErrors.phone = "Enter a 10-digit mobile number.";
    if (password.length < 10) nextErrors.password = "Use at least 10 characters with a letter and a digit.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;
    setPending(true);
    try {
      await api("/api/v1/auth/signup", {
        method: "POST",
        body: JSON.stringify({ full_name: fullName, email, phone, password }),
      });
      window.location.assign(`/verify-email?email=${encodeURIComponent(email)}`);
    } catch (caught) {
      setErrors(fieldErrors(caught));
      setFormError(caught instanceof ApiError ? caught.message : "Could not create the account.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md items-center px-4 py-10">
      <Card className="w-full">
        <p className="text-xs font-semibold uppercase tracking-wide text-moss-700">SunPower Solutions</p>
        <h1 className="mt-1 text-2xl font-semibold">Create a customer account</h1>
        <p className="mt-2 text-sm text-moss-900/80">
          Public registration creates a customer only. Staff accounts are provisioned by the company.
        </p>
        <form className="mt-6 space-y-4" onSubmit={onSubmit} noValidate>
          <TextField label="Full name" name="full_name" autoComplete="name" required error={errors.full_name} />
          <TextField label="Email" name="email" type="email" autoComplete="email" required error={errors.email} />
          <TextField label="Mobile" name="phone" inputMode="numeric" autoComplete="tel" required error={errors.phone} />
          <TextField
            label="Password"
            name="password"
            type="password"
            autoComplete="new-password"
            required
            hint="At least 10 characters, including a letter and a digit."
            error={errors.password}
          />
          {formError ? <ErrorState message={formError} /> : null}
          <Button type="submit" disabled={pending} className="w-full">
            {pending ? "Creating account…" : "Create account"}
          </Button>
        </form>
        <p className="mt-4 text-sm">
          Already registered?{" "}
          <Link className="font-semibold text-moss-800 underline" href="/login">
            Sign in
          </Link>
        </p>
      </Card>
    </main>
  );
}
