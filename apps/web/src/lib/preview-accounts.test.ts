import { expect, it } from "vitest";
import { mkdtempSync, mkdirSync, writeFileSync, chmodSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { previewAccount, previewPassword } from "../../e2e/preview-accounts";
function fixture(){const root=mkdtempSync(join(tmpdir(),"solarops-preview-account-test-"));mkdirSync(join(root,"var"));const path=join(root,"var/LOCAL_PREVIEW_ACCOUNTS.txt");writeFileSync(path,JSON.stringify({environment:"development",accounts:[{role:"sales",identifier:"EMP-SALES-001",password:"test-only-sales-unique"},{role:"warehouse_manager",identifier:"EMP-WHM-001",password:"test-only-manager-unique"}]}),{mode:0o600});return{root,path};}
it("uses each role's private password rather than a shared staff fallback",()=>{const {root}=fixture();expect(previewAccount("sales",root).identifier).toBe("EMP-SALES-001");expect(previewPassword("EMP-WHM-001","stale-shared",root)).toBe("test-only-manager-unique");expect(previewPassword("new-customer@example.test","new-test-customer",root)).toBe("new-test-customer");});
it("refuses unsafe permissions and never exposes malformed credential contents",()=>{const {root,path}=fixture();chmodSync(path,0o644);expect(()=>previewAccount("sales",root)).toThrow("owner-only");chmodSync(path,0o600);writeFileSync(path,'{"private":"DO-NOT-LOG"');expect(()=>previewAccount("sales",root)).toThrow("diagnostic values suppressed");});
it("does not invent a missing role when a private handoff exists",()=>{const {root}=fixture();expect(()=>previewAccount("admin",root)).toThrow("No verified private preview account");});
