import { createElement, Fragment } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { SelectField, TextField } from "@/components/ui";

it("independently labels inputs sharing a form field name", () => {
  const html = renderToStaticMarkup(createElement(Fragment, null,
    createElement(TextField, { name: "serial", label: "Decision serial", hint: "Installed unit" }),
    createElement(TextField, { name: "serial", label: "Exception serial", error: "Check this unit" }),
  ));
  const inputIds = [...html.matchAll(/<input[^>]*?\sid="([^"]+)"/g)].map(match => match[1]);
  const labelTargets = [...html.matchAll(/<label[^>]+for="([^"]+)"/g)].map(match => match[1]);
  expect(inputIds).toHaveLength(2);
  expect(new Set(inputIds).size).toBe(2);
  expect(labelTargets).toEqual(inputIds);
  expect(html).toContain(`aria-describedby="${inputIds[0]}-hint"`);
  expect(html).toContain(`id="${inputIds[0]}-hint"`);
  expect(html).toContain(`aria-describedby="${inputIds[1]}-error"`);
  expect(html).toContain(`id="${inputIds[1]}-error"`);
});
it("preserves an explicit input id for callers", () => {
  const html = renderToStaticMarkup(createElement(TextField, { id: "known-id", name: "label", label: "Label" }));
  expect(html).toContain('for="known-id"');
  expect(html).toContain('id="known-id"');
});
it("independently labels same-name selects and connects each error", () => {
  const html = renderToStaticMarkup(createElement(Fragment, null,
    createElement(SelectField, { name: "state", label: "Decision state", error: "Choose a decision" }),
    createElement(SelectField, { name: "state", label: "Exception state" }),
  ));
  const ids = [...html.matchAll(/<select[^>]*?\sid="([^"]+)"/g)].map(match => match[1]);
  expect(ids).toHaveLength(2);
  expect(new Set(ids).size).toBe(2);
  expect(html).toContain(`aria-describedby="${ids[0]}-error"`);
  expect(html).toContain(`id="${ids[0]}-error"`);
});
