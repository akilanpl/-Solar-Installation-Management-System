import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { ExtensionSettlementUnavailable } from "@/components/extensions";

it("keeps unverified paid activation disabled with an accessible explanation", () => {
  const html = renderToStaticMarkup(createElement(ExtensionSettlementUnavailable));
  expect(html).toMatch(/<button[^>]+disabled=""/);
  expect(html).toContain("Verify payment &amp; activate");
  expect(html).toContain("remains pending");
  expect(html).toContain("a payment reference alone cannot activate coverage");
  const target = /aria-describedby="([^"]+)"/.exec(html)?.[1];
  expect(target).toBeTruthy();
  expect(html).toContain(`id="${target}"`);
});
