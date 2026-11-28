package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strconv"
	"strings"
)

// Anthropic Messages API の形（POST /v1/messages）の要求を、Vertex AI の Claude に付け替えて転送します。
// Pi など、Vertex AI の Claude に直接対応していないハーネス向けです。
// 本文の model を URL に移し、anthropic_version を Vertex 用の値にします。応答の形は同じです。
const maxRequestBody = 32 << 20

func (p *Proxy) handleAnthropic(w http.ResponseWriter, r *http.Request, task Task, path string) {
	if path != "/v1/messages" {
		p.deny(w, r, task.ID, "anthropic path not allowed", http.StatusForbidden)
		return
	}
	if r.Method != http.MethodPost {
		p.deny(w, r, task.ID, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	raw, err := io.ReadAll(io.LimitReader(r.Body, maxRequestBody+1))
	if err != nil || len(raw) > maxRequestBody {
		p.deny(w, r, task.ID, "request body too large or unreadable", http.StatusRequestEntityTooLarge)
		return
	}
	var body map[string]json.RawMessage
	if json.Unmarshal(raw, &body) != nil {
		p.deny(w, r, task.ID, "request body is not a JSON object", http.StatusBadRequest)
		return
	}
	var model string
	var stream bool
	json.Unmarshal(body["model"], &model)
	json.Unmarshal(body["stream"], &stream)
	if model == "" || strings.ContainsAny(model, "/:?#") || !p.cfg.AllowedModels[strings.ToLower(baseModel(model))] {
		p.deny(w, r, task.ID, "model not allowed: "+model, http.StatusForbidden)
		return
	}
	delete(body, "model")
	body["anthropic_version"] = json.RawMessage(`"vertex-2023-10-16"`)
	out, _ := json.Marshal(body)

	tok, err := p.tokenSource.Token()
	if err != nil {
		p.log.Error("token", "task", task.ID, "err", err)
		http.Error(w, "upstream auth unavailable", http.StatusBadGateway)
		return
	}

	const location = "global"
	// global の v1 では rawPredict が 404 になるため、ストリーミングでない要求は v1beta1 に送ります。
	version, method := "v1beta1", "rawPredict"
	if stream {
		version, method = "v1", "streamRawPredict"
	}
	target := &url.URL{
		Scheme: "https",
		Host:   vertexHost(location),
		Path:   "/" + version + "/projects/" + p.cfg.VertexProject + "/locations/" + location + "/publishers/anthropic/models/" + model + ":" + method,
	}
	usage := &usageCounter{}
	rp := &httputil.ReverseProxy{
		Rewrite: func(pr *httputil.ProxyRequest) {
			pr.Out.URL = target
			pr.Out.Host = target.Host
			pr.Out.Body = io.NopCloser(bytes.NewReader(out))
			pr.Out.ContentLength = int64(len(out))
			pr.Out.Header.Set("Content-Length", strconv.Itoa(len(out)))
			// サンドボックスが送ってきた鍵は捨てて、プロキシのトークンに置き換えます。
			pr.Out.Header.Del("X-Api-Key")
			pr.Out.Header.Del("Anthropic-Version") // Vertex では本文の anthropic_version を使います
			pr.Out.Header.Set("Authorization", "Bearer "+tok.AccessToken)
		},
		Transport:     p.transport,
		FlushInterval: -1,
		ModifyResponse: func(resp *http.Response) error {
			resp.Body = usage.wrap(resp.Body)
			return nil
		},
	}

	p.log.Info("anthropic", "task", task.ID, "model", model, "method", method)
	rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
	rp.ServeHTTP(rec, r)
	u := usage.total()
	p.log.Info("anthropic done", "task", task.ID, "model", model, "status", rec.status,
		"input_tokens", u.InputTokens, "output_tokens", u.OutputTokens,
		"cache_read_input_tokens", u.CacheReadInputTokens, "cache_creation_input_tokens", u.CacheCreationInputTokens)
}
