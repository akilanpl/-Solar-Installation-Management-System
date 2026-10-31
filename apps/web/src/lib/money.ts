export function formatPaise(minor: number): string {
  const sign = minor < 0 ? "-" : "";
  const absolute = Math.abs(minor);
  const rupees = Math.floor(absolute / 100);
  const paise = absolute % 100;
  return `${sign}₹${rupees.toLocaleString("en-IN")}.${String(paise).padStart(2, "0")}`;
}
