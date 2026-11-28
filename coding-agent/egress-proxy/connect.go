package main

import (
	"encoding/base64"
	"io"
	"net"
	"net/http"
	"strings"
	"time"
)

// handleConnect は公開レジストリへの HTTPS トンネルだけを許可します。
// サンドボックスは HTTPS_PROXY=http://task:<task-token>@proxy:8080 で使います。
//
// 注意: トンネルの中は TLS なので、HTTP メソッド（GET か PUT か）は見えません。
// 制限できるのは宛先のホストとポートだけです。
func (p *Proxy) handleConnect(w http.ResponseWriter, r *http.Request) {
	task, ok := p.taskFromProxyAuth(r)
	if !ok {
		w.Header().Set("Proxy-Authenticate", `Basic realm="egress-proxy"`)
		p.deny(w, r, "", "proxy auth required", http.StatusProxyAuthRequired)
		return
	}
	host, port, err := net.SplitHostPort(r.Host)
	if err != nil || port != "443" || !p.cfg.RegistryHosts[strings.ToLower(host)] {
		p.deny(w, r, task.ID, "connect destination not allowed", http.StatusForbidden)
		return
	}

	upstream, err := net.DialTimeout("tcp", r.Host, 10*time.Second)
	if err != nil {
		p.log.Error("connect dial", "task", task.ID, "host", r.Host, "err", err)
		http.Error(w, "dial failed", http.StatusBadGateway)
		return
	}
	hj, ok := w.(http.Hijacker)
	if !ok {
		upstream.Close()
		http.Error(w, "hijack unsupported", http.StatusInternalServerError)
		return
	}
	client, _, err := hj.Hijack()
	if err != nil {
		upstream.Close()
		return
	}
	if _, err := client.Write([]byte("HTTP/1.1 200 Connection Established\r\n\r\n")); err != nil {
		client.Close()
		upstream.Close()
		return
	}
	p.log.Info("connect", "task", task.ID, "host", r.Host)
	go func() { io.Copy(upstream, client); upstream.Close() }()
	io.Copy(client, upstream)
	client.Close()
}

func (p *Proxy) taskFromProxyAuth(r *http.Request) (Task, bool) {
	h := r.Header.Get("Proxy-Authorization")
	const prefix = "Basic "
	if !strings.HasPrefix(h, prefix) {
		return Task{}, false
	}
	b, err := base64.StdEncoding.DecodeString(strings.TrimPrefix(h, prefix))
	if err != nil {
		return Task{}, false
	}
	_, token, ok := strings.Cut(string(b), ":")
	if !ok {
		return Task{}, false
	}
	return p.tasks.Lookup(token)
}
