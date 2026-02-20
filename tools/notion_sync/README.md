# Notion Sync Design

## 目的
- Notion SoT と GitHub 証跡を責務分離したまま同期する。
- イベント1/2/3 の最小実装を維持し、I/O契約と再現可能な検証手順を固定する。
- 契約の正本: `docs/SYNC_EVENTS.md`

## 非目的
- 双方向で同一フィールドを同時更新しない。

## 対象イベント（最小3つ）
1. Notion Task 作成/更新 -> GitHub Issue 更新
2. PR 作成/更新 -> Notion Knowledge 更新（リンク+要約）
3. PR merge/CI失敗 -> Notion Task.Execution State 更新

## イベント1 I/O契約（必須）
### Input Event (Event 1)
- `event_type`: `notion.task.created` または `notion.task.updated`
- `payload.task_key`: 必須（形式: `TSK-YYYYMMDD-####`）
  - 互換入力: `taskKey`, `TaskKey`
- `payload.title`: 必須
  - 互換入力: `Title`, `task_title`, `name`
- `payload.summary`: 任意
  - 互換入力: `Summary`, `description`, `Description`
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

## 実行方法（最小実装）
### 実行ファイル
- `tools/notion_sync/event1_dry_run.py`
- `tools/notion_sync/event1_sync.py`（`--mode dry-run|live`）
- `tools/notion_sync/event2_sync.py`（`--mode dry-run|live`）
- `tools/notion_sync/event3_sync.py`（`--mode dry-run|live`）

### 例: 同一TaskKeyを2回（create -> update）
1. 1回目（state初期化）
```bash
python3 tools/notion_sync/event1_dry_run.py \
  --reset-state \
  --event tools/notion_sync/examples/event_with_taskkey.json \
  > /tmp/event1_run1.json
```

2. 2回目（同じTaskKey）
```bash
python3 tools/notion_sync/event1_dry_run.py \
  --event tools/notion_sync/examples/event_with_taskkey.json \
  > /tmp/event1_run2.json
```

### 例: TaskKey欠落（error）
```bash
python3 tools/notion_sync/event1_dry_run.py \
  --event tools/notion_sync/examples/event_missing_taskkey.json \
  > /tmp/event1_missing.json || true
```

### 例: event1_sync.py（dry-run）
```bash
python3 tools/notion_sync/event1_sync.py \
  --mode dry-run \
  --reset-state \
  --event tools/notion_sync/examples/event_with_taskkey.json \
  > /tmp/e1a.json

python3 tools/notion_sync/event1_sync.py \
  --mode dry-run \
  --event tools/notion_sync/examples/event_with_taskkey.json \
  > /tmp/e1b.json
```

### 例: event1_sync.py（live設定確認）
必須環境変数:
- `GITHUB_TOKEN`
- `GITHUB_OWNER`
- `GITHUB_REPO`

```bash
python3 tools/notion_sync/event1_sync.py \
  --mode live \
  --event tools/notion_sync/examples/event_with_taskkey.json \
  --check-config
```

### live 実行オプション（retry/backoff）
- `--max-retries`（default: 3）
- `--backoff-base-sec`（default: 1.0）
- `--backoff-factor`（default: 2.0）
- `--github-api-base`（default: `https://api.github.com`）
- `--live-state`（default: `tools/notion_sync/.live_state.json`）
- live-state 運用: `docs/LIVE_STATE_POLICY.md`

例:
```bash
python3 tools/notion_sync/event1_sync.py \
  --mode live \
  --event tools/notion_sync/examples/event_with_taskkey.json \
  --max-retries 3 \
  --backoff-base-sec 1.0 \
  --backoff-factor 2.0
```

### live モック統合テスト（ローカル）
```bash
python3 tools/notion_sync/tests/test_event1_live_mock.py
```
- 検証内容:
  - live `create -> update`
  - Notion互換入力の正規化（`TaskKey`, `Title`, `Summary.rich_text`）
  - 503 応答時の retry/backoff

## Event2（PR -> Knowledge）
### Input Event (Event 2)
- `event_type`: `github.pr.opened|github.pr.synchronize|github.pr.reopened|github.pr.edited`
- `payload.pr_url`（必須）
- `payload.pr_number`, `payload.title`, `payload.summary`, `payload.repo`, `payload.task_key`（任意）

### Output Action (Event 2)
- `target`: `notion.knowledge`
- `operation`: `upsert | create | update | error`
- `idempotency_key`: `pr_url`

### 設定（live）
- `NOTION_TOKEN`
- `NOTION_KNOWLEDGE_DB_ID`
- `NOTION_KNOWLEDGE_LINK_PROPERTY`（任意、default: `GitHub Canonical Link`）

### 実行例
```bash
python3 tools/notion_sync/event2_sync.py \
  --mode dry-run \
  --event tools/notion_sync/examples/event_pr_opened.json

python3 tools/notion_sync/event2_sync.py \
  --mode live \
  --event tools/notion_sync/examples/event_pr_opened.json \
  --check-config
```

### モック統合テスト
```bash
python3 tools/notion_sync/tests/test_event2_live_mock.py
```

## Event3（merge/CI失敗 -> Task.Execution State）
### Input Event (Event 3)
- `event_type`: `github.pr.merged|github.ci.failed`
- `payload.task_key`（必須）

### Output Action (Event 3)
- `target`: `notion.task`
- `operation`: `update | error`
- `idempotency_key`: `task_key`

### 設定（live）
- `NOTION_TOKEN`
- `NOTION_TASKS_DB_ID`

### 実行例
```bash
python3 tools/notion_sync/event3_sync.py \
  --mode dry-run \
  --event tools/notion_sync/examples/event_pr_merged.json

python3 tools/notion_sync/event3_sync.py \
  --mode live \
  --event tools/notion_sync/examples/event_pr_merged.json \
  --check-config
```

### モック統合テスト
```bash
python3 tools/notion_sync/tests/test_event3_live_mock.py
```

### Event2/3 本番検証（Notion設定済み環境）
```bash
tools/notion_sync/verify_live_event23.sh
```

### Notion DB 項目の自動作成（不足分のみ）
```bash
python3 tools/notion_sync/bootstrap_notion_schema.py --mode live
```

## 同期ルール
- Priority/Due/Owner は Notion only。
- PR状態/CI結果/RUN は GitHub only。
- 失敗時は再試行し、最終失敗は RUN ログへ記録。
