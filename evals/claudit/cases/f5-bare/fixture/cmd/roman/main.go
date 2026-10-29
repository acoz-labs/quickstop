// Command roman converts each argument between integers and Roman numerals.
package main

import (
	"fmt"
	"os"
	"strconv"

	"example.invalid/roman"
)

func main() {
	status := 0
	for _, arg := range os.Args[1:] {
		if n, err := strconv.Atoi(arg); err == nil {
			s, err := roman.Format(n)
			if err != nil {
				fmt.Fprintln(os.Stderr, err)
				status = 1
				continue
			}
			fmt.Println(s)
			continue
		}
		n, err := roman.Parse(arg)
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			status = 1
			continue
		}
		fmt.Println(n)
	}
	os.Exit(status)
}
