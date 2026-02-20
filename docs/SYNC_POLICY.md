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

## 最小イベント3つ（実装済み）
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
- イベント契約の正本は `docs/SYNC_EVENTS.md` を参照。

## エラー処理
- 連携失敗はリトライ（指数バックオフ）。
- Event1/2/3 live の標準値:
  - `max_retries=3`
  - `backoff_base_sec=1.0`
  - `backoff_factor=2.0`
- 永続失敗は `vault/RUN/` へ同期障害ログを出力。
- 不整合検知時は自動修復せず、`docs/DECISIONS.md` の検討事項へ送る。

## 追記: Knowledge 手動索引運用（SPEC-05）
- 正本単位は `SPEC/RUN` とする。
- Notion `Knowledge` は索引として運用し、以下を更新する。
  - `Record Type`（SPEC or RUN）
  - `GitHub Canonical Link`
  - `Summary`
  - `Status`
  - `Owner`
  - `Last Sync`
- PR は `Knowledge` 本体ではなく関連リンクとして扱う。
- 手動索引更新SLA:
  - 標準: `24時間以内`
  - クリティカル（障害/重大仕様変更）: `当日中`
- 自動化優先順位（実装済みの運用優先度）:
  - 優先1: イベント3（PR merge/CI失敗 -> Task.Execution State更新）
  - 優先2: イベント2（PR作成/更新 -> Knowledge更新）
