# Knowledge Ops Guide (SPEC-05)

## 用途
- `SPEC/RUN` を GitHub 正本として運用し、Notion では索引（リンク＋要約）を管理する手順を固定する。

## 対象
- `vault/SPEC/`
- `vault/RUN/`
- Notion `Knowledge` DB（索引）

## 版
- Version: v0.1
- Date: 2026-02-17

## 根拠
- `vault/SPEC/SPEC-05_knowledge_indexing.md`
- `docs/NOTION_SCHEMA.md`
- `docs/SYNC_POLICY.md`

## 差分
- 初版作成（手動運用手順の明文化）

## 最終確認
- Reviewer: codex
- Check date: 2026-02-19
- Publish decision: approved

## 手動運用手順（最小）
1. SPEC作成時
- `vault/SPEC/<spec_file>.md` を正本として保存。
- Notion `Knowledge` に `Record Type=SPEC` で索引レコードを追加。
- `GitHub Canonical Link`, `Summary`, `Status`, `Owner`, `Last Sync` を更新。

2. RUN作成時
- `vault/RUN/<run_file>.md` を正本として保存。
- Notion `Knowledge` に `Record Type=RUN` で索引レコードを追加。
- `GitHub Canonical Link`, `Summary`, `Status`, `Owner`, `Last Sync` を更新。

3. PR連携
- PRは `Knowledge` 本体ではなく関連リンクとして管理する。
- `Knowledge` の正本は常に `SPEC/RUN` 単位。
- 更新SLA:
  - 標準更新: 24時間以内
  - クリティカル更新: 当日中

## 将来自動化ポイント
- 優先1: イベント3（PR merge/CI失敗 -> Notion `Task.Execution State` 自動更新）
- 優先2: イベント2（PR 作成/更新 -> Notion `Knowledge` 自動更新）
