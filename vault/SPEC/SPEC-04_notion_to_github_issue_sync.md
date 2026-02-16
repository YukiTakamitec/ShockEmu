# SPEC: SPEC-04 Notion→GitHub Issue同期（イベント1）

## 目的
- 1スプリント最優先として、イベント1（Notion Task作成/更新 -> GitHub Issue更新）を最小実装で稼働させる。
- 本格同期ではなく、`tools/notion_sync/` に雛形 + 動作確認手順を整備する。

## 変更範囲（ディレクトリ単位）
### OK
- `tools/notion_sync/`
- `docs/`
- `vault/RUN/`

### NG
- イベント2/3の自動化実装
- MCP実装
- 本番環境への常時デプロイ

## 手順
1. `tools/notion_sync/README.md` にイベント1専用のI/O契約を明記する。
2. 最小CLI雛形（例: `plan_sync.sh` or `sync_stub.md`）を追加し、入力JSON -> 予定アクション出力を確認可能にする。
3. GitHub Issue更新の疑似手順（dry-run）を定義する。
4. 手動テスト手順を `vault/RUN/` 用に定義する。
5. エラー時の扱い（リトライ、障害ログ）を明記する。

## 受入基準（コマンドで検証可能）
1. イベント1のI/O定義が存在すること。
- コマンド: `rg -n "Notion Task|GitHub Issue|Input Event|Output Action|idempotency" tools/notion_sync/README.md`
- 期待結果: イベント1向け定義がヒットする。

2. 最小雛形が dry-run できること。
- コマンド: `test -f tools/notion_sync/README.md && rg -n "dry-run|retry|Execution State" tools/notion_sync/README.md`
- 期待結果: dry-run と再試行方針の記述が確認できる。

3. 運用ログ手順があること。
- コマンド: `rg -n "vault/RUN|同期障害|再試行" docs/SYNC_POLICY.md tools/notion_sync/README.md`
- 期待結果: RUN記録と障害時運用の記述がヒットする。

## 生成物
- `tools/notion_sync/README.md`（更新）
- （任意）`tools/notion_sync/sync_stub.md` などの雛形
- `vault/RUN/<...>` テストログ（実施時）

## ロールバック
1. 同期雛形変更を戻す。
- コマンド: `git restore tools/notion_sync/README.md tools/notion_sync/`

## ログ保存先
- `vault/RUN/<YYYYMMDD_HHMM_SPEC-04_sync_event1>.md`

## 根拠
- `docs/SYNC_POLICY.md`
- `tools/notion_sync/README.md`

## 未決事項
- Notion API rate limit 到達時の待機戦略（固定待機か指数バックオフか）。
