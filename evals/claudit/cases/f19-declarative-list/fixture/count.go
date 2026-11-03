// Package quillcount counts words and reading time in Markdown text.
package quillcount

import (
	"strings"
)

// Words counts the words in text, ignoring Markdown punctuation.
func Words(text string) int {
	count := 0
	for _, field := range strings.Fields(text) {
		if strings.Trim(field, "#*_`>-[]()") != "" {
			count++
		}
	}
	return count
}

// ReadingMinutes estimates reading time in whole minutes at 230 words per minute.
func ReadingMinutes(text string) int {
	words := Words(text)
	return (words + 229) / 230
}
