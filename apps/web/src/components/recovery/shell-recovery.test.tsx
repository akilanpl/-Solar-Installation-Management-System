import { describe, it, expect, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { AppShell } from "../shell";
import { ShellPanels } from "./shell-panels";
import type { CurrentUser } from "@/lib/api";
vi.mock("next/navigation",()=>({usePathname:()=>"/customer"}));
const user:CurrentUser={id:"00000000-0000-0000-0000-000000000001",full_name:"Synthetic Explorer",email:"explorer@example.test",phone:"9845012345",role:"customer",account_kind:"customer",employee_code:null,email_verified:true};
describe("recovered shell authorization and honest state",()=>{
 it("keeps customer Phase4 routes reachable without warehouse scanner or role impersonation",()=>{const html=renderToStaticMarkup(<AppShell user={user}>Actual records</AppShell>);for(const path of ["/customer/store","/customer/complaints","/customer/bills","/customer/generation","/customer/warranty-extensions","/security"])expect(html).toContain(`href="${path}"`);expect(html).toContain("liquid-glass-specular-sheen");expect(html).not.toContain("Switch Demo Role");expect(html).not.toContain("Equipment scanner and photo evidence");});
 it("exposes the camera entry only for operational staff and keeps security routes",()=>{for(const role of ["technician","warehouse_staff","warehouse_manager","admin"]){const html=renderToStaticMarkup(<AppShell user={{...user,role,account_kind:"employee"}}>Work</AppShell>);expect(html).toContain("Equipment scanner and photo evidence");expect(html).toContain('href="/security"');}});
 it("does not invent notification events or settlement status",()=>{const html=renderToStaticMarkup(<ShellPanels panel="notifications" onClose={()=>{}} user={user}/>);expect(html).toContain("Notification feed unavailable");expect(html).not.toContain("Reconciled");expect(html).not.toContain("Mark All Read");});
 it("renders profile facts without fake password save or local identity editing",()=>{const html=renderToStaticMarkup(<ShellPanels panel="settings" onClose={()=>{}} user={user}/>);expect(html).toContain(user.email);expect(html).toContain("Profile edits and avatar uploads are unavailable");expect(html).not.toContain("Save All Changes");});
 it("does not render fabricated scanner serials or preloaded evidence",()=>{const html=renderToStaticMarkup(<ShellPanels panel="scanner" onClose={()=>{}} user={{...user,role:"warehouse_staff"}}/>);expect(html).toContain("Exact serial lookup");expect(html).toContain("Enable camera");expect(html).not.toContain("SN-PV540-KA-0985");expect(html).not.toContain("Stock Inward +1");});
});
