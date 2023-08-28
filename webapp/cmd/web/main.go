package main

import (
	"fmt"
	"net/http"

	"github.com/chrptos/dev/webapp/pkg/render"
)

const portNumber string = ":8080"

func main() {
	http.HandleFunc("/", render.Home)
	http.HandleFunc("/about", render.About)

	fmt.Printf("Starting application on port%s", portNumber)
	http.ListenAndServe(portNumber, nil)
}
