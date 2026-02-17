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
1. `tools/notion_sync/README.md` のイベント1 I/O契約に以下を必須記載する。
- TaskKey必須（欠落は `error` 差戻し、create禁止）
- 冪等性（`taskkey:*` label 検索 -> hitでupdate、missでcreate）
- TaskKey埋め込み箇所（title prefix / label / body）
- Notion -> GitHub 更新許可フィールド範囲
2. dry-run 検証シナリオを定義する。
- 同一TaskKeyを2回投入: `create -> update`
- TaskKey欠落投入: `error` かつ createなし
3. dry-run 結果の必須出力項目を定義する（`task_key`, `operation`, `reason`, `matched_issue`）。
4. 運用ログ手順を `vault/RUN/` 向けに整備する。
5. エラー時の扱い（再試行、障害ログ、差戻し条件）を明記する。

## 受入基準（コマンドで検証可能）
1. I/O契約の必須項目が README に存在すること。
- コマンド: `rg -n "TaskKey必須|冪等性|title prefix|Issue Label|Issue Body|更新許可フィールド|検索クエリテンプレート|正規表現" tools/notion_sync/README.md`
- 期待結果: 必須契約5要素がヒットする。

2. 同一TaskKey 2回投入で `create -> update` を検証できること（dry-run仕様）。
- コマンド: `python3 tools/notion_sync/event1_dry_run.py --reset-state --event tools/notion_sync/examples/event_with_taskkey.json > /tmp/event1_run1.json && python3 tools/notion_sync/event1_dry_run.py --event tools/notion_sync/examples/event_with_taskkey.json > /tmp/event1_run2.json && rg -n '"operation": "create"' /tmp/event1_run1.json && rg -n '"operation": "update"' /tmp/event1_run2.json`
- 期待結果: 1回目が create、2回目が update になる。

3. TaskKey欠落で `error` かつ createしないことを検証できること。
- コマンド: `python3 tools/notion_sync/event1_dry_run.py --event tools/notion_sync/examples/event_missing_taskkey.json > /tmp/event1_missing.json || true; rg -n '"operation": "error"' /tmp/event1_missing.json && ! rg -n '"operation": "create"' /tmp/event1_missing.json`
- 期待結果: operation が error で、create は出力されない。

4. Notion -> GitHub 更新対象フィールド一覧が列挙されていること。
- コマンド: `rg -n "更新してよい|更新しない|issue.title|issue.body|issue.labels|priority|due|owner" tools/notion_sync/README.md`
- 期待結果: 更新許可/禁止フィールドが明示されている。

5. 運用ログ手順があること。
- コマンド: `rg -n "vault/RUN|同期障害|再試行" docs/SYNC_POLICY.md tools/notion_sync/README.md`
- 期待結果: RUN記録と障害時運用の記述がヒットする。

6. label厳密形式と検索クエリ例がREADMEに列挙されていること。
- コマンド: `rg -n "^\\s*- 正規表現: `\\^taskkey:TSK-\\[0-9\\]\\{8\\}-\\[0-9\\]\\{4\\}\\$`|repo:<owner>/<repo> is:issue label:taskkey:" tools/notion_sync/README.md`
- 期待結果: label形式の正規表現と Issue検索クエリテンプレがヒットする。

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
- Issue検索のフォールバック戦略（label検索失敗時に title/body 検索を許可するか）。
- エラー分類基準（validation/auth/rate_limit/network/conflict）の分類と再試行可否。
