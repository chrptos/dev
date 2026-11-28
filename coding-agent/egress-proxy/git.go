package main

import (
	"encoding/base64"
	"net/http"
	"net/http/httputil"
	"net/url"
	"regexp"
)

// git smart HTTP のパスだけを通します。
var gitPathRe = regexp.MustCompile(`^/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/(info/refs|git-upload-pack|git-receive-pack)$`)

type gitTarget struct {
	Owner, Repo string
	Endpoint    string // info/refs, git-upload-pack, git-receive-pack
	Op          string // git-upload-pack（読み取り）か git-receive-pack（push）
}

func parseGitPath(path, service string) (gitTarget, bool) {
	m := gitPathRe.FindStringSubmatch(path)
	if m == nil {
		return gitTarget{}, false
	}
	op := m[3]
	if op == "info/refs" {
		if service != "git-upload-pack" && service != "git-receive-pack" {
			return gitTarget{}, false
		}
		op = service
	}
	return gitTarget{Owner: m[1], Repo: m[2], Endpoint: m[3], Op: op}, true
}

func (p *Proxy) handleGit(w http.ResponseWriter, r *http.Request, task Task, path string) {
	t, ok := parseGitPath(path, r.URL.Query().Get("service"))
	if !ok {
		p.deny(w, r, task.ID, "git path not allowed", http.StatusForbidden)
		return
	}
	if !task.allowsRepo(t.Owner, t.Repo) {
		p.deny(w, r, task.ID, "repository not allowed for this task: "+t.Owner+"/"+t.Repo, http.StatusForbidden)
		return
	}
	// push（git-receive-pack）は GitHub 側の Rulesets で agent/* ブランチに限ります。
	// プロキシでは参照名まで検査しません。

	target := &url.URL{
		Scheme:   "https",
		Host:     "github.com",
		Path:     "/" + t.Owner + "/" + t.Repo + ".git/" + t.Endpoint,
		RawQuery: r.URL.RawQuery,
	}

	rp := &httputil.ReverseProxy{
		Rewrite: func(pr *httputil.ProxyRequest) {
			pr.Out.URL = target
			pr.Out.Host = target.Host
			pr.Out.Header.Del("Authorization")
			if p.cfg.GitHubToken != "" {
				cred := base64.StdEncoding.EncodeToString([]byte("x-access-token:" + p.cfg.GitHubToken))
				pr.Out.Header.Set("Authorization", "Basic "+cred)
			}
		},
		Transport:     p.transport,
		FlushInterval: -1,
	}
	p.log.Info("git", "task", task.ID, "repo", t.Owner+"/"+t.Repo, "op", t.Op)
	rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
	rp.ServeHTTP(rec, r)
	p.log.Info("git done", "task", task.ID, "repo", t.Owner+"/"+t.Repo, "op", t.Op, "status", rec.status)
}
