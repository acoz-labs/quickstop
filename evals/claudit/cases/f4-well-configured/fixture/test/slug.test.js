import { test } from "node:test";
import assert from "node:assert/strict";
import { slugify, transliterate } from "../src/index.js";

test("explicit rules run before accent stripping", () => {
  assert.equal(transliterate("Größe"), "groesse");
  assert.equal(transliterate("Café"), "cafe");
});

test("slugify collapses separators and trims dashes", () => {
  assert.equal(slugify("  Hello,   World! "), "hello-world");
  assert.equal(slugify("Fish & Chips"), "fish-and-chips");
});

test("slugify cuts long slugs at a word boundary", () => {
  assert.equal(slugify("alpha beta gamma", { maxLength: 12 }), "alpha-beta");
  assert.equal(slugify("abcdefghij", { maxLength: 4 }), "abcd");
});

test("slugify rejects non-strings", () => {
  assert.throws(() => slugify(42), TypeError);
});
