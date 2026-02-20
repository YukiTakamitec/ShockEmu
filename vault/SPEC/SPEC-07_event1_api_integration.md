# SPEC: SPEC-07 Event1 API integration

## 目的
- Event1（Notion Task -> GitHub Issue）を dry-run から実API接続へ移行する。
- 既存の契約（TaskKey必須、冪等性、更新範囲制約）を壊さずに実行可能化する。

## 変更範囲（ディレクトリ単位）
### OK
- `tools/notion_sync/`
- `vault/RUN/`
- `docs/`（必要最小の追記のみ）

### NG
- Event2/Event3 の実装
- MCP 実装
- Notion only フィールドの GitHub 側更新

## 手順
1. `tools/notion_sync/` に API実行用エントリポイントを追加する。
2. 入力イベントJSON -> GitHub Issue create/update の実通信を実装する。
3. TaskKey欠落時の `error` と create禁止を維持する。
4. dry-run モードを残し、`--mode live|dry-run` で切替可能にする。
5. 検証実行して `vault/RUN/` にログ保存する。

## 受入基準（コマンドで検証可能）
1. 実行CLIが存在すること。
- コマンド: `test -f tools/notion_sync/event1_sync.py`
- 期待結果: ファイルが存在する。

2. dry-runで create->update が維持されること。
- コマンド: `python3 tools/notion_sync/event1_sync.py --mode dry-run --reset-state --event tools/notion_sync/examples/event_with_taskkey.json > /tmp/e1a.json && python3 tools/notion_sync/event1_sync.py --mode dry-run --event tools/notion_sync/examples/event_with_taskkey.json > /tmp/e1b.json && rg -n '"operation": "create"' /tmp/e1a.json && rg -n '"operation": "update"' /tmp/e1b.json`
- 期待結果: 1回目create、2回目update。

3. TaskKey欠落で error になること。
- コマンド: `python3 tools/notion_sync/event1_sync.py --mode dry-run --event tools/notion_sync/examples/event_missing_taskkey.json > /tmp/e1c.json || true; rg -n '"operation": "error"' /tmp/e1c.json`
- 期待結果: error が出力される。

4. liveモードで API呼び出し設定が検証されること。
- コマンド: `python3 tools/notion_sync/event1_sync.py --mode live --event tools/notion_sync/examples/event_with_taskkey.json --check-config`
- 期待結果: 必要環境変数不足時は明示エラー、設定時は接続準備OK。

## 生成物
- `tools/notion_sync/event1_sync.py`
- `tools/notion_sync/README.md`（実API手順追記）
- `vault/RUN/<YYYYMMDD_HHMM_SPEC-07_event1_api_integration>.md`

## ロールバック
1. 実API接続コードを戻す。
- コマンド: `git restore tools/notion_sync/ docs/`

## ログ保存先
- `vault/RUN/<YYYYMMDD_HHMM_SPEC-07_event1_api_integration>.md`

## 根拠
- `vault/SPEC/SPEC-04_notion_to_github_issue_sync.md`
- `tools/notion_sync/README.md`
- `docs/SYNC_POLICY.md`

## 未決事項
- 2026-02-19 決定済み:
  - Notion入力正規化の受理キー:
    - TaskKey: `task_key|taskKey|TaskKey`
    - title: `title|Title|task_title|name`
    - summary: `summary|Summary|description|Description`
  - GitHub Issue body 形式:
    - `TaskKey`, `SourceId`, `SyncedAtUTC`, `Summary` の固定4要素
  - retry/backoff 標準値:
    - `max_retries=3`, `backoff_base_sec=1.0`, `backoff_factor=2.0`
