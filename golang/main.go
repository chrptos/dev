package main

import (
	"fmt"
	"html/template"
	"net/http"
)

const portNumber string = ":8080"

func Home(w http.ResponseWriter, r *http.Request) {
	renderTemplate(w, "home.page.tmpl")
}

func About(w http.ResponseWriter, r *http.Request) {
	renderTemplate(w, "about.page.tmpl")
}

func renderTemplate(w http.ResponseWriter, tmpl string) {
	parsedFile, _ := template.ParseFiles("./templates/" + tmpl)
	err := parsedFile.Execute(w, nil)
	if err != nil {
		fmt.Println(err)
	}
}

func main() {
	http.HandleFunc("/", Home)
	http.HandleFunc("/about", About)

	fmt.Printf("Starting application on port%s", portNumber)
	http.ListenAndServe(portNumber, nil)
}
