package roman

import (
	"errors"
	"testing"
)

func TestFormat(t *testing.T) {
	cases := map[int]string{1: "I", 4: "IV", 9: "IX", 14: "XIV", 1994: "MCMXCIV", 3999: "MMMCMXCIX"}
	for n, want := range cases {
		got, err := Format(n)
		if err != nil || got != want {
			t.Errorf("Format(%d) = %q, %v; want %q", n, got, err, want)
		}
	}
	if _, err := Format(0); !errors.Is(err, ErrRange) {
		t.Errorf("Format(0) error = %v; want ErrRange", err)
	}
}

func TestParse(t *testing.T) {
	if got, err := Parse(" mcmxciv "); err != nil || got != 1994 {
		t.Errorf("Parse = %d, %v; want 1994", got, err)
	}
	for _, bad := range []string{"", "IIII", "VX", "ABC"} {
		if _, err := Parse(bad); !errors.Is(err, ErrSyntax) {
			t.Errorf("Parse(%q) error = %v; want ErrSyntax", bad, err)
		}
	}
}

func TestRoundTrip(t *testing.T) {
	for n := 1; n <= 3999; n++ {
		s, _ := Format(n)
		if got, err := Parse(s); err != nil || got != n {
			t.Fatalf("round trip %d -> %q -> %d, %v", n, s, got, err)
		}
	}
}
