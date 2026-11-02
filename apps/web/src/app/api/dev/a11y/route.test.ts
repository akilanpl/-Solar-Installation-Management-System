import { afterEach, describe, expect, it, vi } from "vitest";
import { GET } from "./route";
afterEach(()=>vi.unstubAllEnvs());
describe("local audit boundary",()=>{
 it("is absent on production even with the explicit flag",async()=>{vi.stubEnv("SOLAROPS_APP_ENV","production");vi.stubEnv("SOLAROPS_LOCAL_AUDIT","on");expect((await GET(new Request("http://127.0.0.1/api/dev/a11y"))).status).toBe(404);});
 it("requires explicit opt in and loopback",async()=>{vi.stubEnv("SOLAROPS_APP_ENV","development");vi.stubEnv("SOLAROPS_LOCAL_AUDIT","");expect((await GET(new Request("http://localhost/api/dev/a11y"))).status).toBe(404);vi.stubEnv("SOLAROPS_LOCAL_AUDIT","on");expect((await GET(new Request("https://example.com/api/dev/a11y"))).status).toBe(404);});
 it("rejects external targets, script injection and unsupported dimensions",async()=>{vi.stubEnv("SOLAROPS_APP_ENV","development");vi.stubEnv("SOLAROPS_LOCAL_AUDIT","on");for(const suffix of ["?path=https://example.com","?path=/customer/%3Cscript%3E","?width=999"]){expect((await GET(new Request("http://localhost/api/dev/a11y"+suffix))).status).toBe(400);}expect((await GET(new Request("http://localhost/api/dev/a11y?path=/customer/payments&width=390"))).status).toBe(200);});
});
