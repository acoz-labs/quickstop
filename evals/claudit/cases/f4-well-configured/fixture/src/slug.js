import { RULES } from "./rules.js";

export function transliterate(text, rules = RULES) {
  let out = "";
  for (const ch of text.toLowerCase()) out += rules[ch] ?? ch;
  // Strip remaining combining marks (é -> e) after the explicit rules run.
  return out.normalize("NFKD").replace(/\p{M}/gu, "");
}

export function slugify(title, { maxLength = 80, rules = RULES } = {}) {
  if (typeof title !== "string") throw new TypeError("title must be a string");
  const slug = transliterate(title, rules)
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  if (slug.length <= maxLength) return slug;
  const cut = slug.slice(0, maxLength + 1).lastIndexOf("-");
  return slug.slice(0, cut > 0 ? cut : maxLength);
}
