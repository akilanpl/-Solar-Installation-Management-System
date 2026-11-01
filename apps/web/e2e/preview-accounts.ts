import { existsSync, readFileSync, statSync } from "node:fs";
import { resolve } from "node:path";
type Account = {role:string;identifier:string;password:string;account_kind?:string};
function privateAccounts(root:string):Account[]|null {
 const path=resolve(root,"var/LOCAL_PREVIEW_ACCOUNTS.txt");if(!existsSync(path))return null;
 if((statSync(path).mode&0o077)!==0)throw new Error("Private preview credentials must have owner-only permissions.");
 try{const data=JSON.parse(readFileSync(path,"utf8"));if(data.environment!=="development"||!Array.isArray(data.accounts))throw new Error();return data.accounts;}catch{throw new Error("Private preview credential document is invalid; diagnostic values suppressed.");}
}
export function previewAccount(role:string,root=resolve(process.cwd(),"../..")):Account {
 const accounts=privateAccounts(root);if(accounts){const account=accounts.find(a=>a.role===role);if(!account?.identifier||!account.password)throw new Error(`No verified private preview account for role ${role}`);return account;}
 if(role==="customer"){const demos=JSON.parse(readFileSync(resolve(root,"var/demo-credentials.json"),"utf8"));return demos["customer.demo@solarops.example.com"];}
 const codes:Record<string,string>={admin:"EMP-ADMIN-001",sales:"EMP-SALES-001",technician:"EMP-TECH-001",warehouse_staff:"EMP-WH-001",warehouse_manager:"EMP-WHM-001",support:"EMP-SUP-001"};
 if(!codes[role])throw new Error("Unsupported preview role");return {role,identifier:codes[role],password:readFileSync(resolve(root,"var/dev-seed-password.txt"),"utf8").trim()};
}
export function previewPassword(identifier:string,fallback:string,root=resolve(process.cwd(),"../..")):string {
 const match=privateAccounts(root)?.find(a=>a.identifier===identifier);if(match)return match.password;
 if(fallback)return fallback;
 if(identifier.startsWith("EMP-"))return readFileSync(resolve(root,"var/dev-seed-password.txt"),"utf8").trim();
 throw new Error("Preview credential unavailable; no password fallback fabricated.");
}
