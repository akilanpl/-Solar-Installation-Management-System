"use client";

import { useEffect, useState } from "react";

import { AccessDenied, ErrorState, LoadingState } from "@/components/ui";
import { DashboardOverview } from "@/components/dashboard-overview";
import { AppShell } from "@/components/shell";
import { api, ApiError, type CurrentUser } from "@/lib/api";
import { canAccessPath, homeForRole, isRole } from "@/lib/access";

export function Workspace({
  path,
  children,
}: {
  path: string;
  children: (user: CurrentUser) => React.ReactNode;
}) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api<{ user: CurrentUser }>("/api/v1/auth/me")
      .then((body) => {
        if (!cancelled) setUser(body.user);
      })
      .catch((caught: unknown) => {
        if (cancelled) return;
        if (caught instanceof ApiError && caught.status === 401) {
          const next = encodeURIComponent(path);
          window.location.assign(`/login?next=${next}`);
          return;
        }
        setError(caught instanceof Error ? caught.message : "Could not load your account.");
      });
    return () => {
      cancelled = true;
    };
  }, [path]);

  if (error) return <div className="p-6"><ErrorState message={error} /></div>;
  if (!user) return <div className="p-6"><LoadingState label="Checking your session" /></div>;
  if (!isRole(user.role) || !canAccessPath(user.role, path)) {
    const home = isRole(user.role) ? homeForRole(user.role) : "/login";
    return <AccessDenied home={home} />;
  }
  return <AppShell user={user}>{["/customer", "/sales", "/technician", "/warehouse", "/support", "/admin"].includes(path) && <DashboardOverview user={user} />}{children(user)}</AppShell>;
}
