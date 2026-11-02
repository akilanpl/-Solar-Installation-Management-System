/** Opt-in loopback QA harness; absent on production or without the local audit flag. */
import { readFile } from "node:fs/promises";
import { join } from "node:path";
export const dynamic = "force-dynamic";
const runner = `document.getElementById('run').addEventListener('click',async()=>{const out=document.querySelector('output');out.dataset.state='running';out.textContent='Running';try{const frame=document.querySelector('iframe');const doc=frame.contentDocument;await doc.fonts.ready;if(!frame.contentWindow.axe)await new Promise((resolve,reject)=>{const script=doc.createElement('script');script.src='/api/dev/a11y?asset=axe';script.onload=resolve;script.onerror=()=>reject(new Error('Axe asset unavailable'));doc.head.appendChild(script);});const result=await frame.contentWindow.axe.run(doc,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});out.textContent=JSON.stringify({url:doc.location.pathname,violations:result.violations.map(v=>({id:v.id,impact:v.impact,help:v.help,nodes:v.nodes.map(n=>({target:n.target,failureSummary:n.failureSummary}))})),incomplete:result.incomplete.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,failureSummary:n.failureSummary}))})),passes:result.passes.length},null,2);out.dataset.state='complete';}catch(e){out.textContent='Audit failed: '+e.message;out.dataset.state='error';}});`;
export async function GET(request: Request) {
  const url = new URL(request.url);
  if (process.env.SOLAROPS_APP_ENV !== "development" || process.env.SOLAROPS_LOCAL_AUDIT !== "on" || !["127.0.0.1", "localhost"].includes(url.hostname)) return new Response("Not found", { status: 404 });
  const headers = { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" };
  if (url.searchParams.get("asset") === "axe") return new Response(await readFile(join(process.cwd(), "node_modules/axe-core/axe.min.js"), "utf8"), { headers: { ...headers, "Content-Type": "text/javascript" } });
  if (url.searchParams.get("asset") === "runner") return new Response(runner, { headers: { ...headers, "Content-Type": "text/javascript" } });
  const path = url.searchParams.get("path") ?? "/login";
  if (!/^\/(login|signup|verify-email|customer|sales|technician|warehouse|support|admin|security)(\/[a-zA-Z0-9_-]+)*$/.test(path)) return new Response("Invalid local page", { status: 400 });
  const width = Number(url.searchParams.get("width") ?? "1280");
  if (![390, 768, 1280].includes(width)) return new Response("Invalid viewport", { status: 400 });
  return new Response(`<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Local accessibility audit</title><script defer src="/api/dev/a11y?asset=runner"></script></head><body><h1>Local accessibility audit</h1><p>Read-only axe scan of the signed-in page. Does not certify screen-reader use or complete WCAG conformance.</p><button id="run">Run accessibility audit</button><pre><output aria-label="Audit result" data-state="ready">Ready</output></pre><iframe title="Page under review" src="${path}" width="${width}" height="900"></iframe></body></html>`, { headers: { ...headers, "Content-Type": "text/html; charset=utf-8" } });
}
