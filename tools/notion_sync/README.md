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

## イベント1 I/O契約（必須）
### Input Event (Event 1)
- `event_type`: `notion.task.created` または `notion.task.updated`
- `payload.task_key`: 必須（形式: `TSK-YYYYMMDD-####`）
- `payload.title`: 必須
- `payload.summary`: 任意
- `payload.priority`, `payload.due`, `payload.owner`: 受け取っても GitHub へは反映しない（Notion only）

TaskKey 欠落時:
- 処理結果は `error`
- `create` も `update` も実行しない（差戻し）

### Output Action (Event 1)
- `target`: `github.issue`
- `operation`: `create | update | error`
- `idempotency_key`: `task_key`

### 冪等性ルール（必須）
1. `label = taskkey:<TaskKey>` で Issue 検索
2. 見つかった場合: `update`
3. 見つからない場合: `create`
4. 同一 TaskKey で 2回実行時の期待挙動: `create -> update`

### 検索クエリテンプレート（必須）
- TaskKey label（厳密形式）:
  - `taskkey:TSK-YYYYMMDD-####`
  - 正規表現: `^taskkey:TSK-[0-9]{8}-[0-9]{4}$`
- GitHub Issue 検索クエリ例:
  - `repo:<owner>/<repo> is:issue label:taskkey:TSK-20260217-0001`
  - `repo:<owner>/<repo> is:issue is:open label:taskkey:TSK-20260217-0001`
- 判定:
  - 1件ヒット: `update`
  - 0件ヒット: `create`
  - 2件以上ヒット: `error`（重複解消まで作成・更新停止）

### TaskKey 埋め込み箇所（必須）
- Issue Title Prefix: `[TSK-YYYYMMDD-####] <title>`
- Issue Label: `taskkey:TSK-YYYYMMDD-####`
- Issue Body: `TaskKey: TSK-YYYYMMDD-####` を先頭セクションに記載

### Notion -> GitHub 更新許可フィールド（必須）
- 更新してよい:
  - `issue.title`（TaskKey prefix を含む）
  - `issue.body`（Summary、関連リンク、同期時刻）
  - `issue.labels`（`taskkey:*`, `status:*`）
- 更新しない:
  - `priority`, `due`, `owner`（Notion only）
  - CI結果/PR状態（GitHub only）

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

## dry-run 検証シナリオ（Event 1）
### シナリオA: 同一TaskKeyを2回流す
1. 1回目の入力（`TSK-20260217-0001`） -> 期待: `operation=create`
2. 2回目の入力（同一TaskKey） -> 期待: `operation=update`

### シナリオB: TaskKey欠落
1. 入力で `payload.task_key` を欠落
2. 期待: `operation=error` かつ `create` は発生しない

### 検証ログ要件
- dry-run 結果に次を必須出力:
  - `task_key`
  - `operation`
  - `reason`（error時）
  - `matched_issue`（update時）

## 同期ルール
- Priority/Due/Owner は Notion only。
- PR状態/CI結果/RUN は GitHub only。
- 失敗時は再試行し、最終失敗は RUN ログへ記録。

## 将来実装の最小構成
- `adapter_notion`（read/write）
- `adapter_github`（read/write）
- `normalizer`（event/action）
- `dispatcher`（routing + retry + idempotency）
