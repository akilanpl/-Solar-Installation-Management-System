"use client";

import { useEffect } from "react";

import { api, ApiError, type CurrentUser } from "@/lib/api";
import { destinationAfterLogin, isRole } from "@/lib/access";
import { LoadingState } from "@/components/ui";

export default function HomePage() {
  useEffect(() => {
    api<{ user: CurrentUser }>("/api/v1/auth/me")
      .then((body) => {
        if (!isRole(body.user.role)) {
          window.location.assign("/login");
          return;
        }
        window.location.assign(destinationAfterLogin(body.user.role, null));
      })
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) {
          window.location.assign("/login");
          return;
        }
        window.location.assign("/login");
      });
  }, []);
  return (
    <main className="p-6">
      <LoadingState label="Opening SolarOps" />
    </main>
  );
}
