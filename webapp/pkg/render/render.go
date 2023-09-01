package render

import (
	"net/http"

	"github.com/chrptos/dev/webapp/pkg/handlers"
)

func Home(w http.ResponseWriter, r *http.Request) {
	handlers.RenderTemplate(w, "home.page.tmpl")
}

func About(w http.ResponseWriter, r *http.Request) {
	handlers.RenderTemplate(w, "about.page.tmpl")
}