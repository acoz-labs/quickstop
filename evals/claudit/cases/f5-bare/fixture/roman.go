// Package roman converts between integers and Roman numerals.
package roman

import (
	"errors"
	"strings"
)

var ErrRange = errors.New("roman: value out of range 1..3999")
var ErrSyntax = errors.New("roman: invalid numeral")

var table = []struct {
	value  int
	symbol string
}{
	{1000, "M"}, {900, "CM"}, {500, "D"}, {400, "CD"},
	{100, "C"}, {90, "XC"}, {50, "L"}, {40, "XL"},
	{10, "X"}, {9, "IX"}, {5, "V"}, {4, "IV"}, {1, "I"},
}

// Format returns the canonical Roman numeral for n.
func Format(n int) (string, error) {
	if n < 1 || n > 3999 {
		return "", ErrRange
	}
	var b strings.Builder
	for _, t := range table {
		for n >= t.value {
			b.WriteString(t.symbol)
			n -= t.value
		}
	}
	return b.String(), nil
}

// Parse reads a canonical Roman numeral, case-insensitively.
func Parse(s string) (int, error) {
	s = strings.ToUpper(strings.TrimSpace(s))
	if s == "" {
		return 0, ErrSyntax
	}
	n, rest := 0, s
	for _, t := range table {
		for strings.HasPrefix(rest, t.symbol) {
			n += t.value
			rest = rest[len(t.symbol):]
		}
	}
	if rest != "" {
		return 0, ErrSyntax
	}
	// Reject non-canonical forms such as IIII or VX by round-tripping.
	if canonical, err := Format(n); err != nil || canonical != s {
		return 0, ErrSyntax
	}
	return n, nil
}
