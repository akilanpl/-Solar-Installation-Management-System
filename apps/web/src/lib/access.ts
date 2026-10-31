export const ROLES = [
  "customer",
  "technician",
  "sales",
  "warehouse_staff",
  "warehouse_manager",
  "support",
  "admin",
] as const;

export type Role = (typeof ROLES)[number];

export type Workspace = "customer" | "technician" | "sales" | "warehouse" | "support" | "admin";

const WORKSPACE_ROLES: Record<Workspace, readonly Role[]> = {
  customer: ["customer"],
  technician: ["technician"],
  sales: ["sales", "admin"],
  warehouse: ["warehouse_staff", "warehouse_manager", "admin"],
  support: ["support", "admin"],
  admin: ["admin"],
};

export function isRole(value: string): value is Role {
  return (ROLES as readonly string[]).includes(value);
}

export function homeForRole(role: Role): string {
  if (role === "warehouse_staff" || role === "warehouse_manager") return "/warehouse";
  return `/${role === "customer" ? "customer" : role}`;
}

export function workspaceFromPath(pathname: string): Workspace | null {
  const match = pathname.match(/^\/(customer|technician|sales|warehouse|support|admin)(?:\/|$)/);
  return (match?.[1] as Workspace | undefined) ?? null;
}

export function canAccessPath(role: Role, pathname: string): boolean {
  const workspace = workspaceFromPath(pathname);
  if (!workspace) return false;
  return WORKSPACE_ROLES[workspace].includes(role);
}

/**
 * Where to send someone after login.
 * `requested` is a path, never the login dropdown. A customer who asked for
 * /admin still lands on /customer.
 */
export function destinationAfterLogin(role: Role, requested: string | null): string {
  const home = homeForRole(role);
  if (!requested || !requested.startsWith("/") || requested.startsWith("//")) return home;
  if (canAccessPath(role, requested)) return requested;
  return home;
}
