# RUN LOG: SPEC-07_event1_api_integration

## 日時
- 2026-02-18

## 対象SPEC
- `vault/SPEC/SPEC-07_event1_api_integration.md`

## 実行コマンド
1. `test -f tools/notion_sync/event1_sync.py`
2. `python3 tools/notion_sync/event1_sync.py --mode dry-run --reset-state --event tools/notion_sync/examples/event_with_taskkey.json > /tmp/e1a.json`
3. `python3 tools/notion_sync/event1_sync.py --mode dry-run --event tools/notion_sync/examples/event_with_taskkey.json > /tmp/e1b.json`
4. `rg -n '"operation": "create"' /tmp/e1a.json`
5. `rg -n '"operation": "update"' /tmp/e1b.json`
6. `python3 tools/notion_sync/event1_sync.py --mode dry-run --event tools/notion_sync/examples/event_missing_taskkey.json > /tmp/e1c.json || true`
7. `rg -n '"operation": "error"' /tmp/e1c.json`
8. `python3 tools/notion_sync/event1_sync.py --mode live --event tools/notion_sync/examples/event_with_taskkey.json --check-config`
9. `GITHUB_TOKEN=dummy GITHUB_OWNER=dummy GITHUB_REPO=dummy python3 tools/notion_sync/event1_sync.py --mode live --event tools/notion_sync/examples/event_with_taskkey.json --check-config`

## 検証結果
### 1) 実行CLI存在
```text
PASS: tools/notion_sync/event1_sync.py exists
```

### 2) dry-run create -> update
```text
17:  "operation": "create",
17:  "operation": "update",
```

### 3) TaskKey欠落でerror
```text
3:  "operation": "error",
RC_MISSING=1
RC_CFG_MISSING=1
```

### 4) live --check-config
- missing config result:
```text
{
  "target": "github.issue",
  "operation": "error",
  "task_key": "",
  "idempotency_key": "",
  "reason": "missing_live_config",
  "missing": [
    "github_token",
    "github_owner",
    "github_repo"
  ]
}
```

- configured result:
```text
3:  "operation": "config_ok",
{
  "target": "github.issue",
  "operation": "config_ok",
  "github_owner": "dummy",
  "github_repo": "dummy"
}
```

## 変更ファイル一覧
- tools/notion_sync/event1_sync.py
- tools/notion_sync/README.md
- vault/SPEC/SPEC-07_event1_api_integration.md

## 変更理由
- Event1 を dry-run 専用から live 設定検証可能な実API接続準備段階へ進めるため。

## リスク
- live 実通信は GitHub API トークン権限とレート制限の影響を受ける。

## 次の確認事項
- live create/update の統合テスト（テスト用repo）
- Notion API入力の正規化
- retry/backoff の定数確定

## 容量メモ
- RUNログは 200KB を目安とし、超過時は分割して相互参照する。
