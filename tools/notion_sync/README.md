# Notion Sync Design (Skeleton)

## 目的
- Notion SoT と GitHub 証跡を責務分離したまま同期する。
- 実装前にイベント・入出力・必要権限を固定する。

## 非目的
- 本READMEは実装コードではない。
- 双方向で同一フィールドを同時更新しない。

## 対象イベント（最小3つ）
1. Notion Task 作成/更新 -> GitHub Issue 更新
2. PR 作成/更新 -> Notion Knowledge 更新（リンク+要約）
3. PR merge/CI失敗 -> Notion Task.Execution State 更新

## 必要権限
### Notion
- Read: Projects/Tasks/Knowledge
- Write: Knowledge（Summary, Link, Status, Last Sync）, Tasks（Execution State, Last Sync）

### GitHub
- Read: PR/Issue/Workflow status
- Write: Issue 作成/更新

## インタフェース定義（雛形）
### Input Event (normalized)
```json
{
  "event_type": "notion.task.updated | github.pr.updated | github.ci.failed",
  "source": "notion|github",
  "source_id": "string",
  "timestamp_utc": "2026-02-16T00:00:00Z",
  "payload": {}
}
```

### Output Action (normalized)
```json
{
  "target": "github.issue | notion.knowledge | notion.task",
  "operation": "create|update",
  "target_id": "string|null",
  "fields": {},
  "idempotency_key": "string"
}
```

## 同期ルール
- Priority/Due/Owner は Notion only。
- PR状態/CI結果/RUN は GitHub only。
- 失敗時は再試行し、最終失敗は RUN ログへ記録。

## 将来実装の最小構成
- `adapter_notion`（read/write）
- `adapter_github`（read/write）
- `normalizer`（event/action）
- `dispatcher`（routing + retry + idempotency）
