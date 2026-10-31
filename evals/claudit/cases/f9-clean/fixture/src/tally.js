// Count words, ignoring punctuation.
export function tally(text) {
  return (text.match(/[\p{L}\p{N}']+/gu) || []).length;
}
