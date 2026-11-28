package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httputil"
	"net/url"
	"regexp"
	"strings"
	"sync"
)

// Claude Code が ANTHROPIC_VERTEX_BASE_URL に送るパスの形。先頭の /v1 は付く場合と付かない場合を両方受けます。
var vertexPathRe = regexp.MustCompile(
	`^(?:/(v1|v1beta1))?/projects/([^/]+)/locations/([^/]+)/publishers/anthropic/models/([^/:]+):(rawPredict|streamRawPredict)$`)

type vertexTarget struct {
	Version  string
	Project  string
	Location string
	Model    string
	Method   string
}

func parseVertexPath(p string) (vertexTarget, bool) {
	m := vertexPathRe.FindStringSubmatch(p)
	if m == nil {
		return vertexTarget{}, false
	}
	v := m[1]
	if v == "" {
		v = "v1"
	}
	return vertexTarget{Version: v, Project: m[2], Location: m[3], Model: m[4], Method: m[5]}, true
}

// vertexHost はロケーションに対応するエンドポイントのホスト名を返します。
func vertexHost(location string) string {
	switch location {
	case "global":
		return "aiplatform.googleapis.com"
	case "us", "eu":
		return "aiplatform." + location + ".rep.googleapis.com"
	default:
		return location + "-aiplatform.googleapis.com"
	}
}

// baseModel は "claude-haiku-4-5@20251001" のようなバージョン付きの ID から、バージョンを除きます。
func baseModel(model string) string {
	if i := strings.IndexByte(model, '@'); i >= 0 {
		return model[:i]
	}
	return model
}

func (p *Proxy) handleVertex(w http.ResponseWriter, r *http.Request, task Task, path string) {
	t, ok := parseVertexPath(path)
	if !ok {
		p.deny(w, r, task.ID, "vertex path not allowed", http.StatusForbidden)
		return
	}
	if t.Project != p.cfg.VertexProject {
		p.deny(w, r, task.ID, "vertex project not allowed", http.StatusForbidden)
		return
	}
	if t.Model != "count-tokens" && !p.cfg.AllowedModels[strings.ToLower(baseModel(t.Model))] {
		p.deny(w, r, task.ID, "model not allowed: "+t.Model, http.StatusForbidden)
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

	target := &url.URL{
		Scheme: "https",
		Host:   vertexHost(t.Location),
		Path:   "/" + t.Version + "/projects/" + t.Project + "/locations/" + t.Location + "/publishers/anthropic/models/" + t.Model + ":" + t.Method,
	}
	usage := &usageCounter{}
	rp := &httputil.ReverseProxy{
		Rewrite: func(pr *httputil.ProxyRequest) {
			pr.Out.URL = target
			pr.Out.Host = target.Host
			pr.Out.Header.Del("Authorization")
			pr.Out.Header.Set("Authorization", "Bearer "+tok.AccessToken)
		},
		Transport:     p.transport,
		FlushInterval: -1, // ストリーミングの応答をすぐに流す
		ModifyResponse: func(resp *http.Response) error {
			resp.Body = usage.wrap(resp.Body)
			return nil
		},
	}

	p.log.Info("vertex", "task", task.ID, "location", t.Location, "model", t.Model, "method", t.Method)
	rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
	rp.ServeHTTP(rec, r)
	u := usage.total()
	p.log.Info("vertex done", "task", task.ID, "model", t.Model, "status", rec.status,
		"input_tokens", u.InputTokens, "output_tokens", u.OutputTokens,
		"cache_read_input_tokens", u.CacheReadInputTokens, "cache_creation_input_tokens", u.CacheCreationInputTokens)
}

type usage struct {
	InputTokens              int `json:"input_tokens"`
	OutputTokens             int `json:"output_tokens"`
	CacheReadInputTokens     int `json:"cache_read_input_tokens"`
	CacheCreationInputTokens int `json:"cache_creation_input_tokens"`
}

// usageCounter は応答を流しながら、Messages API の usage を集計します。
// ストリーミング（SSE）では message_start と message_delta、通常の応答では本文の usage を読みます。
type usageCounter struct {
	mu   sync.Mutex
	u    usage
	buf  bytes.Buffer
	sse  bool
	body bytes.Buffer // SSE でない場合の本文（上限付き）
}

const maxBufferedBody = 4 << 20

func (c *usageCounter) wrap(rc io.ReadCloser) io.ReadCloser {
	return &countingBody{rc: rc, c: c}
}

func (c *usageCounter) feed(b []byte) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.body.Len() < maxBufferedBody {
		c.body.Write(b)
	}
	c.buf.Write(b)
	for {
		line, err := c.buf.ReadBytes('\n')
		if err != nil {
			c.buf.Reset()
			c.buf.Write(line) // 行の途中は次回に回す
			return
		}
		c.line(bytes.TrimSpace(line))
	}
}

func (c *usageCounter) line(l []byte) {
	if !bytes.HasPrefix(l, []byte("data:")) {
		return
	}
	c.sse = true
	var ev struct {
		Type    string `json:"type"`
		Message struct {
			Usage usage `json:"usage"`
		} `json:"message"`
		Usage         usage        `json:"usage"`
		UsageMetadata *geminiUsage `json:"usageMetadata"`
	}
	if json.Unmarshal(bytes.TrimSpace(l[len("data:"):]), &ev) != nil {
		return
	}
	if ev.UsageMetadata != nil {
		// Gemini は塊ごとに累計を返すので、最後の値で上書きします。
		c.u = ev.UsageMetadata.toUsage()
		return
	}
	switch ev.Type {
	case "message_start":
		c.add(ev.Message.Usage)
	case "message_delta":
		// message_delta の output_tokens は累計なので、最後の値で上書きします。
		c.u.OutputTokens = ev.Usage.OutputTokens
	}
}

func (c *usageCounter) add(u usage) {
	c.u.InputTokens += u.InputTokens
	c.u.OutputTokens += u.OutputTokens
	c.u.CacheReadInputTokens += u.CacheReadInputTokens
	c.u.CacheCreationInputTokens += u.CacheCreationInputTokens
}

func (c *usageCounter) total() usage {
	c.mu.Lock()
	defer c.mu.Unlock()
	if !c.sse {
		var resp struct {
			Usage         usage        `json:"usage"`
			UsageMetadata *geminiUsage `json:"usageMetadata"`
		}
		if json.Unmarshal(c.body.Bytes(), &resp) == nil {
			if resp.UsageMetadata != nil {
				return resp.UsageMetadata.toUsage()
			}
			return resp.Usage
		}
	}
	return c.u
}

type countingBody struct {
	rc io.ReadCloser
	c  *usageCounter
}

func (b *countingBody) Read(p []byte) (int, error) {
	n, err := b.rc.Read(p)
	if n > 0 {
		b.c.feed(p[:n])
	}
	return n, err
}

func (b *countingBody) Close() error { return b.rc.Close() }

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (s *statusRecorder) WriteHeader(code int) {
	s.status = code
	s.ResponseWriter.WriteHeader(code)
}

func (s *statusRecorder) Flush() {
	if f, ok := s.ResponseWriter.(http.Flusher); ok {
		f.Flush()
	}
}
