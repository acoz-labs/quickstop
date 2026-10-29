import { test } from "node:test";
import assert from "node:assert/strict";
import { createInvoice, formatCents, lineItem, renderInvoice, taxCents, totals } from "../src/index.js";

test("formatCents groups thousands and keeps two decimals", () => {
  assert.equal(formatCents(123456789), "1,234,567.89 EUR");
  assert.equal(formatCents(-5, "USD"), "-0.05 USD");
});

test("taxCents rounds half up on basis points", () => {
  assert.equal(taxCents(1000, "standard"), 200);
  assert.equal(taxCents(1005, "reduced"), 70);
  assert.throws(() => taxCents(100, "luxury"), RangeError);
});

test("totals applies the discount pro rata before tax", () => {
  const items = [lineItem("Widget", 2, 10), lineItem("Book", 1, 20, "reduced")];
  assert.deepEqual(totals(items, 1000), {
    net: 4000, discount: 1000, discountedNet: 3000, tax: 405, gross: 3405,
  });
  assert.throws(() => totals(items, 5000), RangeError);
});

test("createInvoice validates the number and renders", () => {
  assert.throws(() => createInvoice({ number: "42", customer: "A", items: [] }));
  const inv = createInvoice({ number: "INV-2024-0001", customer: "Acme", items: [lineItem("Widget", 1, 9.99)] });
  assert.match(renderInvoice(inv), /Total\s+11\.99 EUR/);
});
