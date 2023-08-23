package main

import (
	"fmt"
	"net/http"
)

const portNumber string = ":8080"

func Home(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "Hello, World!!")
}

func About(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "2 + 2 is %d", addValues(2, 2))
}

func addValues(a, b int) int {
	return a + b
}

func main() {
	http.HandleFunc("/", Home)
	http.HandleFunc("/about", About)

	fmt.Printf("Starting application on port%s", portNumber)
	http.ListenAndServe(portNumber, nil)
}
