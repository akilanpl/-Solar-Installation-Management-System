"use client";
import { useEffect } from "react";
export default function Page() {
  useEffect(() => { window.location.replace("/customer/complaints"); }, []);
  return <p className="p-6 text-sm">Opening your complaints…</p>;
}
