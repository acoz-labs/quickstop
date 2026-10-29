import { formatCents } from "./money.js";
import { lineNet } from "./invoice.js";

const WIDTH = 60;

function row(left, right) {
  const gap = Math.max(1, WIDTH - left.length - right.length);
  return left + " ".repeat(gap) + right;
}

export function renderInvoice(invoice) {
  const money = (cents) => formatCents(cents, invoice.currency);
  const lines = [
    `Invoice ${invoice.number}`,
    `Bill to: ${invoice.customer}`,
    "-".repeat(WIDTH),
  ];
  for (const item of invoice.items) {
    lines.push(row(`${item.quantity} x ${item.description}`, money(lineNet(item))));
  }
  lines.push("-".repeat(WIDTH));
  lines.push(row("Net", money(invoice.net)));
  if (invoice.discount) lines.push(row("Discount", money(-invoice.discount)));
  lines.push(row("Tax", money(invoice.tax)));
  lines.push(row("Total", money(invoice.gross)));
  return lines.join("\n") + "\n";
}
