package main

import (
	"encoding/base64"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"golang.org/x/oauth2"
)

// upstreamTransport は外向きの要求を記録し、決まった応答を返します。
type upstreamTransport struct {
	got  *http.Request
	body string
	ct   string
}

func (u *upstreamTransport) RoundTrip(r *http.Request) (*http.Response, error) {
	u.got = r
	ct := u.ct
	if ct == "" {
		ct = "application/json"
	}
	return &http.Response{
		StatusCode: http.StatusOK,
		Header:     http.Header{"Content-Type": {ct}},
		Body:       io.NopCloser(strings.NewReader(u.body)),
		Request:    r,
	}, nil
}

func newTestProxy(up *upstreamTransport) *Proxy {
	return &Proxy{
		cfg: Config{
			VertexProject:    "proj",
			AllowedModels:    csvSet("claude-haiku-4-5"),
			AllowedLocations: csvSet("global,us"),
			RegistryHosts:    csvSet("registry.npmjs.org"),
			GitHubToken:      "gh-secret",
		},
		tasks:       fileTaskStore{"tok": {ID: "task-1", Repos: []string{"acme/app"}}},
		tokenSource: oauth2.StaticTokenSource(&oauth2.Token{AccessToken: "gcp-secret"}),
		transport:   up,
		log:         slog.New(slog.NewTextHandler(io.Discard, nil)),
	}
}

func do(p *Proxy, method, target string, hdr map[string]string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, target, strings.NewReader(`{}`))
	for k, v := range hdr {
		r.Header.Set(k, v)
	}
	w := httptest.NewRecorder()
	p.ServeHTTP(w, r)
	return w
}

const vertexPath = "/projects/proj/locations/global/publishers/anthropic/models/claude-haiku-4-5@20251001:streamRawPredict"

func TestVertexInjectsCredentials(t *testing.T) {
	for _, prefix := range []string{"", "/v1"} {
		up := &upstreamTransport{body: `{}`}
		p := newTestProxy(up)
		w := do(p, "POST", "/t/tok/vertex"+prefix+vertexPath, map[string]string{"Authorization": "Bearer fake"})
		if w.Code != http.StatusOK {
			t.Fatalf("prefix %q: status %d: %s", prefix, w.Code, w.Body)
		}
		if got := up.got.URL.String(); got != "https://aiplatform.googleapis.com/v1"+vertexPath {
			t.Errorf("prefix %q: upstream url %s", prefix, got)
		}
		if got := up.got.Header.Get("Authorization"); got != "Bearer gcp-secret" {
			t.Errorf("prefix %q: authorization %q", prefix, got)
		}
	}
}

func TestVertexRegionalHost(t *testing.T) {
	cases := map[string]string{
		"global":   "aiplatform.googleapis.com",
		"us":       "aiplatform.us.rep.googleapis.com",
		"us-east5": "us-east5-aiplatform.googleapis.com",
	}
	for loc, want := range cases {
		if got := vertexHost(loc); got != want {
			t.Errorf("%s: got %s want %s", loc, got, want)
		}
	}
}

func TestVertexDenies(t *testing.T) {
	cases := []struct {
		name, path string
		want       int
	}{
		{"no token", "/vertex/v1" + vertexPath, http.StatusUnauthorized},
		{"unknown token", "/t/nope/vertex/v1" + vertexPath, http.StatusUnauthorized},
		{"other project", "/t/tok/vertex/v1/projects/other/locations/global/publishers/anthropic/models/claude-haiku-4-5:rawPredict", http.StatusForbidden},
		{"model not allowed", "/t/tok/vertex/v1/projects/proj/locations/global/publishers/anthropic/models/claude-opus-5-5:rawPredict", http.StatusForbidden},
		{"other publisher", "/t/tok/vertex/v1/projects/proj/locations/global/publishers/google/models/gemini:generateContent", http.StatusForbidden},
		{"location not allowed", "/t/tok/vertex/v1/projects/proj/locations/asia-northeast1/publishers/anthropic/models/claude-haiku-4-5:rawPredict", http.StatusForbidden},
		// ロケーションは転送先のホスト名になるので、ホスト名を変える値は通さない
		{"location host injection", "/t/tok/vertex/v1/projects/proj/locations/evil.example%23/publishers/anthropic/models/claude-haiku-4-5:rawPredict", http.StatusForbidden},
		{"location with port", "/t/tok/vertex/v1/projects/proj/locations/evil.example:443/publishers/anthropic/models/claude-haiku-4-5:rawPredict", http.StatusForbidden},
		{"unknown route", "/t/tok/other", http.StatusForbidden},
	}
	for _, c := range cases {
		up := &upstreamTransport{}
		w := do(newTestProxy(up), "POST", c.path, nil)
		if w.Code != c.want {
			t.Errorf("%s: status %d want %d", c.name, w.Code, c.want)
		}
		if up.got != nil {
			t.Errorf("%s: request reached upstream", c.name)
		}
	}
}

func TestUsageFromSSE(t *testing.T) {
	sse := strings.Join([]string{
		`event: message_start`,
		`data: {"type":"message_start","message":{"usage":{"input_tokens":12,"cache_read_input_tokens":100,"output_tokens":1}}}`,
		``,
		`event: message_delta`,
		`data: {"type":"message_delta","usage":{"output_tokens":7}}`,
		``,
	}, "\n")
	c := &usageCounter{}
	body := c.wrap(io.NopCloser(strings.NewReader(sse)))
	// 小さな塊で読み、行の途中で切れても集計できることを確かめます。
	buf := make([]byte, 7)
	for {
		if _, err := body.Read(buf); err != nil {
			break
		}
	}
	u := c.total()
	if u.InputTokens != 12 || u.OutputTokens != 7 || u.CacheReadInputTokens != 100 {
		t.Errorf("usage %+v", u)
	}
}

func TestUsageFromJSON(t *testing.T) {
	c := &usageCounter{}
	body := c.wrap(io.NopCloser(strings.NewReader(`{"usage":{"input_tokens":3,"output_tokens":4}}`)))
	io.ReadAll(body)
	if u := c.total(); u.InputTokens != 3 || u.OutputTokens != 4 {
		t.Errorf("usage %+v", u)
	}
}

func TestGitAllowedRepo(t *testing.T) {
	up := &upstreamTransport{}
	p := newTestProxy(up)
	w := do(p, "GET", "/t/tok/github/acme/app.git/info/refs?service=git-upload-pack", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("status %d: %s", w.Code, w.Body)
	}
	if got := up.got.URL.String(); got != "https://github.com/acme/app.git/info/refs?service=git-upload-pack" {
		t.Errorf("upstream url %s", got)
	}
	want := "Basic " + base64.StdEncoding.EncodeToString([]byte("x-access-token:gh-secret"))
	if got := up.got.Header.Get("Authorization"); got != want {
		t.Errorf("authorization %q", got)
	}
}

func TestGitDenies(t *testing.T) {
	cases := map[string]string{
		"other repo":    "/t/tok/github/acme/secret.git/info/refs?service=git-upload-pack",
		"bad service":   "/t/tok/github/acme/app.git/info/refs?service=evil",
		"non-git path":  "/t/tok/github/acme/app/settings",
		"path traverse": "/t/tok/github/acme/../other/app.git/git-upload-pack",
	}
	for name, path := range cases {
		up := &upstreamTransport{}
		w := do(newTestProxy(up), "GET", path, nil)
		if w.Code != http.StatusForbidden {
			t.Errorf("%s: status %d", name, w.Code)
		}
		if up.got != nil {
			t.Errorf("%s: request reached upstream", name)
		}
	}
}

func TestConnectDenies(t *testing.T) {
	auth := "Basic " + base64.StdEncoding.EncodeToString([]byte("task:tok"))
	cases := []struct {
		name, host, auth string
		want             int
	}{
		{"no auth", "registry.npmjs.org:443", "", http.StatusProxyAuthRequired},
		{"bad token", "registry.npmjs.org:443", "Basic " + base64.StdEncoding.EncodeToString([]byte("task:nope")), http.StatusProxyAuthRequired},
		{"host not allowed", "example.com:443", auth, http.StatusForbidden},
		{"port not allowed", "registry.npmjs.org:22", auth, http.StatusForbidden},
	}
	for _, c := range cases {
		r := httptest.NewRequest("CONNECT", "http://"+c.host, nil)
		r.Host = c.host
		if c.auth != "" {
			r.Header.Set("Proxy-Authorization", c.auth)
		}
		w := httptest.NewRecorder()
		newTestProxy(&upstreamTransport{}).ServeHTTP(w, r)
		if w.Code != c.want {
			t.Errorf("%s: status %d want %d", c.name, w.Code, c.want)
		}
	}
}

func TestPlainHTTPProxyDenied(t *testing.T) {
	r := httptest.NewRequest("GET", "http://example.com/", nil)
	w := httptest.NewRecorder()
	newTestProxy(&upstreamTransport{}).ServeHTTP(w, r)
	if w.Code != http.StatusForbidden {
		t.Errorf("status %d", w.Code)
	}
}

func TestRedactPath(t *testing.T) {
	if got := redactPath("/t/secret-token/vertex/x"); strings.Contains(got, "secret-token") {
		t.Errorf("token leaked: %s", got)
	}
}

func TestGeminiRewritesToVertex(t *testing.T) {
	up := &upstreamTransport{body: `{}`}
	p := newTestProxy(up)
	p.cfg.AllowedModels = csvSet("gemini-2.5-flash")
	w := do(p, "POST", "/t/tok/gemini/v1beta/models/gemini-2.5-flash:streamGenerateContent?alt=sse",
		map[string]string{"X-Goog-Api-Key": "fake"})
	if w.Code != http.StatusOK {
		t.Fatalf("status %d: %s", w.Code, w.Body)
	}
	want := "https://aiplatform.googleapis.com/v1/projects/proj/locations/global/publishers/google/models/gemini-2.5-flash:streamGenerateContent?alt=sse"
	if got := up.got.URL.String(); got != want {
		t.Errorf("upstream url %s", got)
	}
	if got := up.got.Header.Get("Authorization"); got != "Bearer gcp-secret" {
		t.Errorf("authorization %q", got)
	}
	if got := up.got.Header.Get("X-Goog-Api-Key"); got != "" {
		t.Errorf("api key forwarded: %q", got)
	}
}

func TestGeminiDenies(t *testing.T) {
	cases := map[string]string{
		"model not allowed": "/t/tok/gemini/v1beta/models/gemini-3-pro:generateContent",
		"other method":      "/t/tok/gemini/v1beta/models/claude-haiku-4-5:embedContent",
		"other path":        "/t/tok/gemini/v1beta/files",
	}
	for name, path := range cases {
		up := &upstreamTransport{}
		w := do(newTestProxy(up), "POST", path, nil)
		if w.Code != http.StatusForbidden {
			t.Errorf("%s: status %d", name, w.Code)
		}
		if up.got != nil {
			t.Errorf("%s: request reached upstream", name)
		}
	}
}

func TestUsageFromGeminiSSE(t *testing.T) {
	sse := "data: {\"usageMetadata\":{\"promptTokenCount\":50,\"candidatesTokenCount\":2}}\n\n" +
		"data: {\"usageMetadata\":{\"promptTokenCount\":50,\"candidatesTokenCount\":9,\"thoughtsTokenCount\":3,\"cachedContentTokenCount\":20}}\n\n"
	c := &usageCounter{}
	io.ReadAll(c.wrap(io.NopCloser(strings.NewReader(sse))))
	if u := c.total(); u.InputTokens != 30 || u.OutputTokens != 12 || u.CacheReadInputTokens != 20 {
		t.Errorf("usage %+v", u)
	}
}

func TestAnthropicRewritesToVertex(t *testing.T) {
	up := &upstreamTransport{body: `{}`}
	p := newTestProxy(up)
	r := httptest.NewRequest("POST", "/t/tok/anthropic/v1/messages?beta=true",
		strings.NewReader(`{"model":"claude-haiku-4-5","stream":true,"max_tokens":10,"messages":[]}`))
	r.Header.Set("X-Api-Key", "fake")
	r.Header.Set("Anthropic-Version", "2023-06-01")
	w := httptest.NewRecorder()
	p.ServeHTTP(w, r)
	if w.Code != http.StatusOK {
		t.Fatalf("status %d: %s", w.Code, w.Body)
	}
	want := "https://aiplatform.googleapis.com/v1/projects/proj/locations/global/publishers/anthropic/models/claude-haiku-4-5:streamRawPredict"
	if got := up.got.URL.String(); got != want {
		t.Errorf("upstream url %s", got)
	}
	if got := up.got.Header.Get("Authorization"); got != "Bearer gcp-secret" {
		t.Errorf("authorization %q", got)
	}
	if up.got.Header.Get("X-Api-Key") != "" || up.got.Header.Get("Anthropic-Version") != "" {
		t.Errorf("client headers forwarded")
	}
	b, _ := io.ReadAll(up.got.Body)
	if strings.Contains(string(b), `"model"`) || !strings.Contains(string(b), `"anthropic_version":"vertex-2023-10-16"`) {
		t.Errorf("body %s", b)
	}
}

func TestAnthropicDenies(t *testing.T) {
	cases := map[string]string{
		"model not allowed": `{"model":"claude-opus-5-5"}`,
		"model with path":   `{"model":"claude-haiku-4-5/../x"}`,
		"no model":          `{}`,
	}
	for name, body := range cases {
		up := &upstreamTransport{}
		r := httptest.NewRequest("POST", "/t/tok/anthropic/v1/messages", strings.NewReader(body))
		w := httptest.NewRecorder()
		newTestProxy(up).ServeHTTP(w, r)
		if w.Code != http.StatusForbidden {
			t.Errorf("%s: status %d", name, w.Code)
		}
		if up.got != nil {
			t.Errorf("%s: request reached upstream", name)
		}
	}
	w := do(newTestProxy(&upstreamTransport{}), "POST", "/t/tok/anthropic/v1/complete", nil)
	if w.Code != http.StatusForbidden {
		t.Errorf("other path: status %d", w.Code)
	}
}
