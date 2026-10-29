// Tax rates are basis points (1 bp = 0.01%) keyed by category.

export const RATES = {
  standard: 2000,
  reduced: 700,
  zero: 0,
};

export function rateFor(category) {
  if (!(category in RATES)) {
    throw new RangeError(`unknown tax category: ${category}`);
  }
  return RATES[category];
}

export function taxCents(netCents, category) {
  return Math.round((netCents * rateFor(category)) / 10000);
}
