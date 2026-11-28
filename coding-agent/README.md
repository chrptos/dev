# coding-agent

Slack から依頼すると、隔離されたサンドボックスで作業して GitHub に PR を作る、社内向けのコーディングエージェントです。GCP 上で動かします。

現在は設計と検証の段階です。

## 構成

- [docs/design.md](docs/design.md)：設計ドキュメント（MVP）。付録 A に検証結果があります
- [egress-proxy/](egress-proxy/)：サンドボックスの通信を受け、認証情報を付けて転送するプロキシの試作
