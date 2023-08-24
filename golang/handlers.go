package main

import (
	"fmt"
	"html/template"
	"net/http"
)

func renderTemplate(w http.ResponseWriter, tmpl string) {
	parsedFile, _ := template.ParseFiles("./templates/" + tmpl)
	err := parsedFile.Execute(w, nil)
	if err != nil {
		fmt.Println(err)
	}
}