package quillcount

import (
	"fmt"
	"testing"
)

func TestWords(t *testing.T) {
	if got := Words("# Title\n\nTwo *words*"); got != 3 {
		t.Fatalf("Words = %d, want 3", got)
	}
}

func ExampleReadingMinutes() {
	fmt.Println(ReadingMinutes("one two three"))
	// Output: 1
}
