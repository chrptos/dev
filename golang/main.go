package main

import (
	"errors"
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

func Devide(w http.ResponseWriter, r *http.Request) {
	f, err := divideValues(100.0, 0.0)
	if err != nil {
		fmt.Fprint(w, err)
	} else {
		fmt.Fprintf(w, "100 / 100 is %f", f)
	}
}

func addValues(a, b int) int {
	return a + b
}

func divideValues(a, b float32) (float32, error) {
	if b == 0 {
		err := errors.New("cannot devide by 0")
		return 0, err
	} else {
		return a / b, nil
	}
}

func main() {
	http.HandleFunc("/", Home)
	http.HandleFunc("/about", About)
	http.HandleFunc("/divide", Devide)

	fmt.Printf("Starting application on port%s", portNumber)
	http.ListenAndServe(portNumber, nil)
}
