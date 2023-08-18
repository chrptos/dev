package main

import (
	"fmt"
	"log"
)

type Entry struct {
	AuthorID string
	Author string
	TitleID string
	Title string
	InfoURL string
	ZipURL string
}

func funcfindEntries(siteURL string) ([]Entry, error) {
	//処理
}

func main() {
	listURL := "https://www.aozora.gr.jp/index_pages/person879.html"

	entries, err := findEntries(listURL)
	if err != nil {
		log.Fatal(err)
	}
	for _, entry := range entries {
		fmt.Println(entry.Title, entry.ZipURL)
	}
}