package main

import (
	"encoding/json"
	"net/http"
)

type jsonResponse struct {
	Error bool `json:"error"`
	Message string `json:"message"`
}

type credentials struct {
	Username string `json:"email"`
	Password string `json:"password"`		
}

func (app *application) Login(w http.ResponseWriter, r *http.Request) {

	var creds credentials
	var payload jsonResponse

	err := json.NewDecoder(r.Body).Decode(&creds)

	if err != nil {
		app.errorLog.Println("invalid json")

		payload.Error = true
		payload.Message = "invalid json"

		out, err := json.MarshalIndent(payload, "", "\t")
		if err != nil {
			app.errorLog.Println(err)
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write(out)

		return
	}

	// authenticate
	app.infoLog.Println(creds.Username, creds.Password)

	// send response
	payload.Error = false
	payload.Message = "Signed in"
	out, err := json.MarshalIndent(payload, "", "\t")
	if err != nil {
		app.errorLog.Println(err)
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(out)

	return
}