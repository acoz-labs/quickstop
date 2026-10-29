import { toCents } from "./money.js";
import { taxCents } from "./tax.js";

export function lineItem(description, quantity, unitPrice, category = "standard") {
  if (!description) throw new Error("description is required");
  if (!Number.isInteger(quantity) || quantity <= 0) {
    throw new RangeError("quantity must be a positive integer");
  }
  return { description, quantity, unitCents: toCents(unitPrice), category };
}

export function lineNet(item) {
  return item.quantity * item.unitCents;
}

export function totals(items, discountCents = 0) {
  const net = items.reduce((sum, item) => sum + lineNet(item), 0);
  if (discountCents > net) throw new RangeError("discount exceeds net total");
  // Discount is applied pro rata before tax, per line.
  const factor = net === 0 ? 0 : (net - discountCents) / net;
  const tax = items.reduce(
    (sum, item) => sum + taxCents(Math.round(lineNet(item) * factor), item.category),
    0,
  );
  const discountedNet = net - discountCents;
  return { net, discount: discountCents, discountedNet, tax, gross: discountedNet + tax };
}

export function createInvoice({ number, customer, items, discountCents = 0, currency = "EUR" }) {
  if (!/^INV-\d{4}-\d{4}$/.test(number)) {
    throw new Error(`invoice number must look like INV-2024-0001, got ${number}`);
  }
  return { number, customer, items, currency, ...totals(items, discountCents) };
}
