import type { QuotationLineResponse } from "@/lib/api";
import { formatInrFromPaise } from "@/lib/format";

export function QuoteLines({
  lines,
  material,
  installation,
  discount,
  tax,
  taxRateBps,
  total,
}: {
  lines: QuotationLineResponse[];
  material: number;
  installation: number;
  discount: number;
  tax: number;
  taxRateBps: number;
  total: number;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-moss-100 text-xs uppercase tracking-wide text-moss-800">
          <tr>
            <th className="px-3 py-2">Item</th>
            <th className="px-3 py-2">Kind</th>
            <th className="px-3 py-2">Qty</th>
            <th className="px-3 py-2">Unit price</th>
            <th className="px-3 py-2">Line total</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line) => (
            <tr key={`${line.sort_order}-${line.description}`} className="border-b border-moss-50">
              <td className="px-3 py-2">
                {line.description}
                {line.component_code ? <span className="block text-xs text-moss-800/70">{line.component_code}</span> : null}
              </td>
              <td className="px-3 py-2">{line.line_kind}</td>
              <td className="px-3 py-2">{line.quantity} {line.unit}</td>
              <td className="px-3 py-2">{formatInrFromPaise(line.unit_price_minor)}</td>
              <td className="px-3 py-2">{formatInrFromPaise(line.line_total_minor)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <dl className="mt-4 space-y-1 text-sm">
        <Row label="Materials" value={formatInrFromPaise(material)} />
        <Row label="Installation" value={formatInrFromPaise(installation)} />
        <Row label="Discount" value={formatInrFromPaise(discount)} />
        <Row label={`Tax (${(taxRateBps / 100).toFixed(2)}%)`} value={formatInrFromPaise(tax)} />
        <Row label="Total" value={formatInrFromPaise(total)} strong />
      </dl>
    </div>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={`flex justify-between gap-4 ${strong ? "font-semibold" : ""}`}>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
