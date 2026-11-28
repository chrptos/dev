# testing-playground

Cindy Sridharan の「Testing in Production」の図にあるテスト・検証手法を、一通り試すための練習用プロジェクト。

対象は小さな注文 API（商品登録・注文・割引・税・在庫）。Python 3.12 / FastAPI / SQLite。

## セットアップ

```bash
uv sync
make all        # lint + 型チェック + セキュリティ + 全テスト（カバレッジ）
```

## 進め方（ステージ）

| ステージ | 内容 | 状態 |
|---|---|---|
| 1 | 小さなアプリ ＋ Pre-production のテスト ＋ CI | ✅ |
| 2 | Docker Compose ＋ OpenTelemetry/Grafana ＋ Sentry ＋ k6（load / soak / monitoring） | 未着手 |
| 3 | kind ＋ Argo Rollouts ＋ Unleash（canary / traffic shaping / feature flag / shadowing） | 未着手 |
| 4 | Chaos Mesh ＋ アラート（chaos testing / Game day） | 未着手 |

## ステージ1: 手法ごとの場所と実行方法

| 手法 | 場所 | 実行 |
|---|---|---|
| Unit | `tests/unit/` | `make unit` |
| Property-based（Hypothesis） | `tests/property/test_pricing_properties.py` | `make property` |
| Stateful property-based | `tests/property/test_repository_stateful.py` | `make property` |
| Component（本物の SQLite） | `tests/component/` | `make component` |
| Functional（HTTP API） | `tests/functional/` | `make functional` |
| Acceptance（Given/When/Then） | `tests/acceptance/` | `make acceptance` |
| Regression | `tests/regression/` | `make regression` |
| Fuzz ＋ Contract（Schemathesis） | `tests/fuzz/` | `make fuzz` |
| Contract（OpenAPI スナップショット） | `tests/contract/` | `make contract` |
| Config | `tests/config/` | `make config` |
| Coverage（90% 未満で失敗） | — | `make coverage` |
| Benchmark | `tests/benchmark/` | `make bench` |
| Mutation（mutmut） | `src/shop/pricing.py` が対象 | `make mutation` |
| Smoke | `tests/smoke/` | `make serve` の後に別ターミナルで `make smoke` |
| Lint（Ruff） | — | `make lint` |
| Static analysis（mypy strict） | — | `make typecheck` |
| Static analysis（Bandit） | — | `make security` |

CI は `.github/workflows/testing-playground.yml`（GitHub Actions の仕様でリポジトリのルートに置く必要がある）。

## 実際に見つかったもの（学びのメモ）

### Fuzz test（Schemathesis）: 初回実行で 5 件
1. `GET /products/9223372036854775808` → **500**。SQLite の INTEGER（64bit）を超える値で `OverflowError`
2. `GET /orders/{同上}` → 同じく 500
3. `POST /products {"stock": false}` → **201 で受理**。Pydantic が bool を 0 に変換していた（契約違反）
4. スキーマの `maximum: 9223372036854775807` が、JSON の数値（float）として **2^63 に丸められ**、境界がずれていた → 上限を 2^53-1 に変更
5. 壊れた JSON に対する 400 が、OpenAPI に書かれていなかった

ほかに、strict モードで `0.0` を拒否したら「JSON Schema では `0.0` も integer」と指摘された。

### Mutation test（mutmut）: カバレッジ 100% でも 69 個中 16 個の変異が生き残った
- `//` → `/`（整数除算 → 浮動小数点除算）が検出されなかった。`100.0 == 100` が True になるため
- 税率の既定値 `10` → `11` が検出されなかった。既定値を使うテストがなかった
- エラーメッセージの変更が検出されなかった

テストを追加し、69 個すべてを検出できるようにした。**カバレッジは「実行されたか」しか見ておらず、「正しさを確かめたか」は見ていない。**

## まだ試していない Pre-production の手法
- Formal verification（TLA+ など）
- Penetration test（OWASP ZAP。サーバーを起動して自分の環境だけに対して実行する）
- Threat modeling（STRIDE）
- Performance / Load（k6。ステージ2）
- UI/UX・Usability（UI がまだない）
