# RUN LOG: SPEC-05_knowledge_indexing

## 日時
- 2026-02-17 03:02:00

## 対象SPEC
- `vault/SPEC/SPEC-05_knowledge_indexing.md`

## 実行コマンド
1. `rg -n "SPEC/RUN|Knowledge|索引|Canonical Link|PRは関連リンク" docs/NOTION_SCHEMA.md docs/SYNC_POLICY.md`
2. `rg -n "手動|更新手順|Last Sync|Summary" docs/SYNC_POLICY.md vault/templates/run_log_template.md`
3. `rg -n "将来|自動化|イベント2|イベント3" docs/SYNC_POLICY.md docs/DECISIONS.md`

## 差分
- 変更ファイル:
  - `vault/knowledge/knowledge_ops_guide.md`
  - `docs/SYNC_POLICY.md`
  - `docs/NOTION_SCHEMA.md`
- 変更要約:
  - SPEC/RUN正本 + Notion索引の手動運用手順を最小構成で文書化

## 検証
### 1) SPEC/RUN単位正本の規則
```text
docs/SYNC_POLICY.md:32:2. PR 作成/更新 -> Notion Knowledge 更新（リンク+要約）
docs/SYNC_POLICY.md:34:- Action: Knowledge レコードを作成/更新
docs/SYNC_POLICY.md:37:  - Notion: Canonical Link, Summary, Status, Last Sync
docs/SYNC_POLICY.md:56:## 追記: Knowledge 手動索引運用（SPEC-05）
docs/SYNC_POLICY.md:57:- 正本単位は `SPEC/RUN` とする。
docs/SYNC_POLICY.md:58:- Notion `Knowledge` は索引として運用し、以下を更新する。
docs/SYNC_POLICY.md:60:  - `GitHub Canonical Link`
docs/SYNC_POLICY.md:65:- PR は `Knowledge` 本体ではなく関連リンクとして扱う。
docs/SYNC_POLICY.md:67:  - イベント2（PR作成/更新 -> Knowledge更新）
docs/NOTION_SCHEMA.md:17:- `Related Knowledge` (relation -> Knowledge)
docs/NOTION_SCHEMA.md:34:## Database: Knowledge
docs/NOTION_SCHEMA.md:36:- `Knowledge ID` (rich_text, unique)
docs/NOTION_SCHEMA.md:37:- `Record Type` (select: SPEC/RUN/Meeting/Research/Deliverable/Agent/FAQ, required)
docs/NOTION_SCHEMA.md:38:- `GitHub Canonical Link` (url, required)
docs/NOTION_SCHEMA.md:49:- Deliverable は必ず `GitHub Canonical Link` を持つ。
docs/NOTION_SCHEMA.md:50:- FAQ/軽メモ以外は Canonical Link 必須。
docs/NOTION_SCHEMA.md:53:## 追記: Knowledge索引ルール（SPEC-05）
docs/NOTION_SCHEMA.md:54:- `SPEC/RUN` 単位を正本とし、`Knowledge` は索引として運用する。
docs/NOTION_SCHEMA.md:55:- `Knowledge` レコードの必須運用項目:
docs/NOTION_SCHEMA.md:57:  - `GitHub Canonical Link`
docs/NOTION_SCHEMA.md:62:- PR は `Knowledge` 本体ではなく関連リンクとして扱う。
```

### 2) 手動運用手順の確認
```text
docs/SYNC_POLICY.md:37:  - Notion: Canonical Link, Summary, Status, Last Sync
docs/SYNC_POLICY.md:44:  - Notion: Execution State, Last Sync
docs/SYNC_POLICY.md:56:## 追記: Knowledge 手動索引運用（SPEC-05）
docs/SYNC_POLICY.md:61:  - `Summary`
docs/SYNC_POLICY.md:64:  - `Last Sync`
```

### 3) 将来自動化ポイントの確認
```text
docs/SYNC_POLICY.md:24:## 最小イベント3つ（初期導入）
docs/SYNC_POLICY.md:66:- 将来自動化対象:
docs/SYNC_POLICY.md:67:  - イベント2（PR作成/更新 -> Knowledge更新）
docs/SYNC_POLICY.md:68:  - イベント3（PR merge/CI失敗 -> Task.Execution State更新）
docs/DECISIONS.md:18:- 決定が必要: 初期フェーズでどこまで自動化するか。
```

## 残課題
- Knowledge索引更新SLA（当日中/24時間以内）の確定
- イベント2/3の自動化優先順位の確定

## 容量メモ
- RUNログは 200KB を目安とし、超過時は分割して相互参照する。
