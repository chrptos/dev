package render

import (
	"net/http"
)

// TODO: refactor
func Home(w http.ResponseWriter, r *http.Request) {
	RenderTemplate(w, "home.page.tmpl")
}

func About(w http.ResponseWriter, r *http.Request) {
	RenderTemplate(w, "about.page.tmpl")
}