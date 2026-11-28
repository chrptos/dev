package main

import (
	"net/http"
	"net/http/httputil"
	"net/url"
	"regexp"
	"strings"
)

// Gemini API の形（Pi などの google-generative-ai クライアントが送る形）のパス。
// 例: /v1beta/models/gemini-2.5-flash:streamGenerateContent?alt=sse
// これを Vertex AI の publishers/google のパスに付け替えて転送します。
var geminiPathRe = regexp.MustCompile(`^/v1(?:beta)?/models/([A-Za-z0-9_.-]+):(generateContent|streamGenerateContent|countTokens)$`)

func (p *Proxy) handleGemini(w http.ResponseWriter, r *http.Request, task Task, path string) {
	m := geminiPathRe.FindStringSubmatch(path)
	if m == nil {
		p.deny(w, r, task.ID, "gemini path not allowed", http.StatusForbidden)
		return
	}
	model, method := m[1], m[2]
	if !p.cfg.AllowedModels[strings.ToLower(model)] {
		p.deny(w, r, task.ID, "model not allowed: "+model, http.StatusForbidden)
		return
	}
	if r.Method != http.MethodPost {
		p.deny(w, r, task.ID, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	tok, err := p.tokenSource.Token()
	if err != nil {
		p.log.Error("token", "task", task.ID, "err", err)
		http.Error(w, "upstream auth unavailable", http.StatusBadGateway)
		return
	}

	const location = "global"
	q := url.Values{}
	if r.URL.Query().Get("alt") == "sse" {
		q.Set("alt", "sse")
	}
	target := &url.URL{
		Scheme:   "https",
		Host:     vertexHost(location),
		Path:     "/v1/projects/" + p.cfg.VertexProject + "/locations/" + location + "/publishers/google/models/" + model + ":" + method,
		RawQuery: q.Encode(),
	}
	usage := &usageCounter{}
	rp := &httputil.ReverseProxy{
		Rewrite: func(pr *httputil.ProxyRequest) {
			pr.Out.URL = target
			pr.Out.Host = target.Host
			// サンドボックスが送ってきた鍵は捨てて、プロキシのトークンに置き換えます。
			pr.Out.Header.Del("X-Goog-Api-Key")
			pr.Out.Header.Set("Authorization", "Bearer "+tok.AccessToken)
		},
		Transport:     p.transport,
		FlushInterval: -1,
		ModifyResponse: func(resp *http.Response) error {
			resp.Body = usage.wrap(resp.Body)
			return nil
		},
	}

	p.log.Info("gemini", "task", task.ID, "model", model, "method", method)
	rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
	rp.ServeHTTP(rec, r)
	u := usage.total()
	p.log.Info("gemini done", "task", task.ID, "model", model, "status", rec.status,
		"input_tokens", u.InputTokens, "output_tokens", u.OutputTokens,
		"cache_read_input_tokens", u.CacheReadInputTokens)
}

// geminiUsage は Gemini の usageMetadata です。ストリーミングでは塊ごとに累計が入ります。
type geminiUsage struct {
	PromptTokenCount        int `json:"promptTokenCount"`
	CandidatesTokenCount    int `json:"candidatesTokenCount"`
	ThoughtsTokenCount      int `json:"thoughtsTokenCount"`
	CachedContentTokenCount int `json:"cachedContentTokenCount"`
}

func (g *geminiUsage) toUsage() usage {
	return usage{
		InputTokens:          g.PromptTokenCount - g.CachedContentTokenCount,
		OutputTokens:         g.CandidatesTokenCount + g.ThoughtsTokenCount,
		CacheReadInputTokens: g.CachedContentTokenCount,
	}
}
