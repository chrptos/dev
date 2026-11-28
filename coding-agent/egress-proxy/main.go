// egress-proxy は、サンドボックスからの通信をすべて受けて、
// 許可した宛先にだけ認証情報を付けて転送する試作のプロキシです。
//
// 経路:
//
//	/t/<task-token>/vertex/...   Vertex AI（Claude）へのリバースプロキシ
//	/t/<task-token>/anthropic/... Anthropic Messages API の形の要求を Vertex AI（Claude）に付け替えて転送
//	/t/<task-token>/gemini/...   Gemini API の形の要求を Vertex AI（Gemini）に付け替えて転送
//	/t/<task-token>/github/...   GitHub の git smart HTTP へのリバースプロキシ
//	CONNECT host:443             公開レジストリへのトンネル（許可リストのみ）
//
// それ以外の通信はすべて拒否します。
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"strings"
	"time"

	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
)

// Task は1つのタスクに許可された範囲です。本番では受付 Bot が Firestore に登録します。
type Task struct {
	ID    string   `json:"id"`
	Repos []string `json:"repos"` // "owner/repo"
}

func (t Task) allowsRepo(owner, repo string) bool {
	want := strings.ToLower(owner + "/" + repo)
	for _, r := range t.Repos {
		if strings.ToLower(r) == want {
			return true
		}
	}
	return false
}

// TaskStore はタスクトークンからタスクを引きます。
type TaskStore interface {
	Lookup(token string) (Task, bool)
}

type fileTaskStore map[string]Task

func (s fileTaskStore) Lookup(token string) (Task, bool) {
	t, ok := s[token]
	return t, ok
}

type Config struct {
	Listen        string
	VertexProject string
	AllowedModels map[string]bool
	RegistryHosts map[string]bool
	GitHubToken   string
}

type Proxy struct {
	cfg         Config
	tasks       TaskStore
	tokenSource oauth2.TokenSource
	transport   http.RoundTripper
	log         *slog.Logger
}

func main() {
	log := slog.New(slog.NewJSONHandler(os.Stdout, nil))

	cfg := Config{
		Listen:        envOr("LISTEN_ADDR", "127.0.0.1:8080"),
		VertexProject: os.Getenv("VERTEX_PROJECT"),
		AllowedModels: csvSet(envOr("ALLOWED_MODELS", "claude-sonnet-5-5,claude-haiku-5-5")),
		RegistryHosts: csvSet(envOr("REGISTRY_HOSTS",
			"registry.npmjs.org,pypi.org,files.pythonhosted.org,proxy.golang.org,sum.golang.org")),
		GitHubToken: os.Getenv("GITHUB_TOKEN"),
	}
	if cfg.VertexProject == "" {
		log.Error("VERTEX_PROJECT is required")
		os.Exit(1)
	}

	tasks, err := loadTasks(os.Getenv("TASKS_FILE"))
	if err != nil {
		log.Error("load tasks", "err", err)
		os.Exit(1)
	}

	// ローカルでは ADC、Compute Engine 上ではメタデータサーバーからトークンを取ります。
	ts, err := google.DefaultTokenSource(context.Background(), "https://www.googleapis.com/auth/cloud-platform")
	if err != nil {
		log.Error("google credentials", "err", err)
		os.Exit(1)
	}

	p := &Proxy{cfg: cfg, tasks: tasks, tokenSource: ts, transport: http.DefaultTransport, log: log}
	srv := &http.Server{
		Addr:              cfg.Listen,
		Handler:           p,
		ReadHeaderTimeout: 10 * time.Second,
	}
	log.Info("listening", "addr", cfg.Listen, "project", cfg.VertexProject)
	if err := srv.ListenAndServe(); err != nil {
		log.Error("serve", "err", err)
		os.Exit(1)
	}
}

func (p *Proxy) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodConnect {
		p.handleConnect(w, r)
		return
	}
	// 平文の HTTP をフォワードプロキシとして使う要求（絶対 URL）は拒否します。
	if r.URL.IsAbs() {
		p.deny(w, r, "", "plain http proxying is not allowed", http.StatusForbidden)
		return
	}
	if r.URL.Path == "/healthz" {
		w.WriteHeader(http.StatusOK)
		return
	}

	token, rest, ok := splitTaskPath(r.URL.Path)
	if !ok {
		p.deny(w, r, "", "missing task token", http.StatusUnauthorized)
		return
	}
	task, ok := p.tasks.Lookup(token)
	if !ok {
		p.deny(w, r, "", "unknown task token", http.StatusUnauthorized)
		return
	}

	switch {
	case strings.HasPrefix(rest, "/vertex/"):
		p.handleVertex(w, r, task, strings.TrimPrefix(rest, "/vertex"))
	case strings.HasPrefix(rest, "/anthropic/"):
		p.handleAnthropic(w, r, task, strings.TrimPrefix(rest, "/anthropic"))
	case strings.HasPrefix(rest, "/gemini/"):
		p.handleGemini(w, r, task, strings.TrimPrefix(rest, "/gemini"))
	case strings.HasPrefix(rest, "/github/"):
		p.handleGit(w, r, task, strings.TrimPrefix(rest, "/github"))
	default:
		p.deny(w, r, task.ID, "unknown route", http.StatusForbidden)
	}
}

// splitTaskPath は "/t/<token>/rest..." を token と "/rest..." に分けます。
func splitTaskPath(path string) (token, rest string, ok bool) {
	if !strings.HasPrefix(path, "/t/") {
		return "", "", false
	}
	s := strings.TrimPrefix(path, "/t/")
	i := strings.IndexByte(s, '/')
	if i <= 0 {
		return "", "", false
	}
	return s[:i], s[i:], true
}

func (p *Proxy) deny(w http.ResponseWriter, r *http.Request, taskID, reason string, code int) {
	p.log.Warn("deny", "task", taskID, "method", r.Method, "path", redactPath(r.URL.Path), "host", r.Host, "reason", reason)
	http.Error(w, reason, code)
}

// redactPath はログに残すパスからタスクトークンを消します。
func redactPath(path string) string {
	if _, rest, ok := splitTaskPath(path); ok {
		return "/t/***" + rest
	}
	return path
}

func loadTasks(path string) (fileTaskStore, error) {
	if path == "" {
		return nil, fmt.Errorf("TASKS_FILE is required")
	}
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var s fileTaskStore
	if err := json.Unmarshal(b, &s); err != nil {
		return nil, err
	}
	return s, nil
}

func envOr(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

func csvSet(s string) map[string]bool {
	m := map[string]bool{}
	for _, v := range strings.Split(s, ",") {
		if v = strings.TrimSpace(v); v != "" {
			m[strings.ToLower(v)] = true
		}
	}
	return m
}
