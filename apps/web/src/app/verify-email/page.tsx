"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Button, ErrorState, TextField } from "@/components/ui";
import { AuthFrame } from "@/components/auth-frame";
import { api, ApiError, fieldErrors } from "@/lib/api";

function VerifyForm() {
  const params = useSearchParams();
  const [email, setEmail] = useState(params.get("email") ?? "");
  const [code, setCode] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [pending, setPending] = useState(false);
  useEffect(() => {
    document.body.dataset.verifyReady = "1";
  }, []);
  const devMailbox = process.env.NEXT_PUBLIC_SOLAROPS_ENV === "development";

  async function loadCapturedCode() {
    setFormError(null);
    try {
      const message = await api<{ code: string }>(`/api/v1/dev/mailbox/${encodeURIComponent(email)}`);
      setCode(message.code);
      setMessage("Loaded the code from the local development mailbox. This button is not available in production.");
    } catch (caught) {
      setFormError(caught instanceof ApiError ? caught.message : "No local mailbox message was found.");
    }
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    if (!/^[0-9]{6}$/.test(code)) {
      setErrors({ code: "Enter the 6-digit code." });
      return;
    }
    setPending(true);
    try {
      await api("/api/v1/auth/verify-email", {
        method: "POST",
        body: JSON.stringify({ email, code }),
      });
      window.location.assign("/login?verified=1");
    } catch (caught) {
      setErrors(fieldErrors(caught));
      setFormError(caught instanceof ApiError ? caught.message : "Verification failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthFrame><div className="auth-verification">
        <h1 className="auth-form-heading">Verify your email</h1>
        <p className="mt-2 text-sm text-moss-900/80">
          Enter the one-time code from your verification message. It expires in 10 minutes and works once.
        </p>
        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <TextField label="Email" name="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          <TextField
            label="Verification code"
            name="code"
            inputMode="numeric"
            autoComplete="one-time-code"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            error={errors.code}
            required
          />
          {message ? <p className="text-sm text-moss-800">{message}</p> : null}
          {formError ? <ErrorState message={formError} /> : null}
          <Button type="submit" disabled={pending} className="w-full">
            {pending ? "Checking…" : "Verify email"}
          </Button>
        </form>
        {devMailbox ? (
          <div className="mt-4 rounded-md bg-sun-100 p-3 text-sm">
            <p className="font-semibold text-sun-700">Development mailbox</p>
            <p className="mt-1">
              No SMTP server is configured. The API wrote the code to the local mailbox file. Production does not expose this.
            </p>
            <Button type="button" variant="secondary" className="mt-3" onClick={loadCapturedCode}>
              Load code from local mailbox
            </Button>
          </div>
        ) : null}
        <p className="mt-4 text-sm">
          <Link className="font-semibold text-moss-800 underline" href="/login">
            Back to sign in
          </Link>
        </p>
      </div></AuthFrame>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyForm />
    </Suspense>
  );
}
