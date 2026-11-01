import { readdirSync, statSync } from "node:fs";
import { resolve, relative, sep } from "node:path";

export function discoverPages() {
  const root = resolve(process.cwd(), "src/app");
  const pages: string[] = [];
  function visit(directory: string) {
    for (const name of readdirSync(directory)) {
      const path = resolve(directory, name);
      if (statSync(path).isDirectory()) visit(path);
      else if (name === "page.tsx") {
        const route = "/" + relative(root, directory).split(sep).filter(p => p !== "." && !p.startsWith("(")).join("/");
        pages.push(route);
      }
    }
  }
  visit(root);
  return pages.sort();
}
export function owner(route: string) {
  if(route==="/warehouse/approvals")return "warehouse_manager";
  const area = route.split("/")[1];
  return ["customer", "sales", "technician", "support", "admin"].includes(area) ? area
    : area === "warehouse" ? "warehouse_staff" : area === "security" ? "customer" : "public";
}
