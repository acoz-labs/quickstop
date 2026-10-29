// All amounts are integer cents to avoid floating-point drift.

export function toCents(amount) {
  if (typeof amount !== "number" || !Number.isFinite(amount)) {
    throw new TypeError(`not a finite number: ${amount}`);
  }
  return Math.round(amount * 100);
}

export function fromCents(cents) {
  return cents / 100;
}

export function formatCents(cents, currency = "EUR") {
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(cents);
  const whole = Math.floor(abs / 100).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const frac = String(abs % 100).padStart(2, "0");
  return `${sign}${whole}.${frac} ${currency}`;
}
