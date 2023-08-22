package main

import (
	"fmt"
	"net/http"
)

func main() {
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		n, err := fmt.Fprintf(w, "Hello, World!")
		if err != nil {
			fmt.Println("err")
		}
		// fmt.Println(fmt.Sprintf("Number of bytes written: %d", n))
		fmt.Printf("Number of bytes written: %d\n", n)
	})
	http.ListenAndServe(":8080", nil)
}
