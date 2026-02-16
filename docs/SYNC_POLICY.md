# Sync Policy

## 目的
- Notion/GitHub 間同期での責務衝突を防ぎ、更新源を固定する。

## 更新責務
- Notion only:
  - Priority
  - Due
  - Owner
  - 意思決定ログ

- GitHub only:
  - PR状態
  - CI結果
  - 実行ログ（RUN）
  - 差分
  - Deliverable版

## 双方向禁止ルール
- 同一フィールドを双方向で更新しない。
- 片方向の更新失敗時は再試行し、逆方向で補正しない。

## 最小イベント3つ（初期導入）
1. Notion Task 作成/更新 -> GitHub Issue 更新
- Trigger: Task 作成、Status/Priority/Due/Owner 変更
- Action: Issue 作成またはタイトル/本文/ラベル更新
- Write scope:
  - Notion: 変更なし
  - GitHub: Issue metadata

2. PR 作成/更新 -> Notion Knowledge 更新（リンク+要約）
- Trigger: pull_request opened/synchronize/reopened/edited
- Action: Knowledge レコードを作成/更新
- Write scope:
  - GitHub: 変更なし
  - Notion: Canonical Link, Summary, Status, Last Sync

3. PR merge/CI失敗 -> Notion Task の Execution State 更新
- Trigger: pull_request closed(merged), workflow_run completed(failure)
- Action: Task.Execution State を更新
- Write scope:
  - GitHub: 変更なし
  - Notion: Execution State, Last Sync

## 正規化ルール
- 時刻は UTC ISO8601 で保持。
- ステータスはマッピングテーブルで正規化。
- URL は canonical 化（PR/Issue/Blob path の正規形式）。

## エラー処理
- 連携失敗はリトライ（指数バックオフ）。
- 永続失敗は `vault/RUN/` へ同期障害ログを出力。
- 不整合検知時は自動修復せず、`docs/DECISIONS.md` の検討事項へ送る。
