import type { Metadata } from "next";

import "./globals.css";
import "@/styles/teammate-tokens.css";
import "@/styles/teammate-auth.css";
import "@/styles/teammate-shell.css";
import "@/styles/teammate-dock.css";
import "@/styles/teammate-header.css";
import "@/styles/teammate-dashboard.css";
import "@/styles/teammate-records.css";
import "@/styles/teammate-transaction.css";
import "@/styles/teammate-receipt.css";
import "@/styles/teammate-surveys.css";
import "@/styles/integration.css";

export const metadata: Metadata = {
  title: "SolarOps",
  description: "Solar installation operations for SunPower Solutions",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a
          href="#content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-white focus:px-3 focus:py-2"
        >
          Skip to content
        </a>
        <div id="content">{children}</div>
      </body>
    </html>
  );
}
