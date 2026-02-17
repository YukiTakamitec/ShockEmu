# SPEC: SPEC-03 TaskKey仕様

## 目的
- `TaskKey = TSK-YYYYMMDD-####` を運用キーとして標準化し、NotionとGitHubを紐付ける。
- タイトル/ラベル/PR本文への埋め込み規則と、例外・移行ルールを決める。

## 変更範囲（ディレクトリ単位）
### OK
- `docs/`
- `vault/templates/`

### NG
- 同期実装コード（本SPECでは仕様定義のみ）
- Notion本番データの一括書換

## 手順
1. TaskKeyフォーマットを `TSK-YYYYMMDD-####` に固定し、採番責任を Notion に置く。
2. GitHub埋め込み規則を定義する。
- Issue title: `[TSK-YYYYMMDD-####] <summary>`
- Issue labels: `taskkey:TSK-...`
- PR本文: `TaskKey: TSK-...`
3. 既存タスク移行ルールを定義する（旧キーは `LegacyTaskKey` で保持）。
4. 例外（キー未発行時）の暫定処理を定義する（`TSK-PENDING` 禁止、必ずNotionで採番後に着手）。

## 受入基準（コマンドで検証可能）
1. TaskKey規則が文書化されていること。
- コマンド: `rg -n "TSK-[0-9]{8}-[0-9]{4}|TaskKey|LegacyTaskKey" docs/SYNC_POLICY.md docs/NOTION_SCHEMA.md docs/CONSTITUTION.md`
- 期待結果: フォーマットと移行キーの記述がヒットする。

2. テンプレにTaskKey項目が追加されていること。
- コマンド: `rg -n "TaskKey|TSK-" vault/templates/spec_template.md vault/templates/run_log_template.md`
- 期待結果: SPEC/RUN テンプレにTaskKey記載欄が存在する。

3. 埋め込み規則が検証可能な形で記載されていること。
- コマンド: `rg -n "Issue title|labels|PR本文|taskkey:" docs/SYNC_POLICY.md`
- 期待結果: 3箇所の埋め込み規則がヒットする。

## 生成物
- `docs/SYNC_POLICY.md`（更新）
- `docs/NOTION_SCHEMA.md`（更新）
- `vault/templates/spec_template.md`（更新）
- `vault/templates/run_log_template.md`（更新）

## ロールバック
1. 仕様更新を戻す。
- コマンド: `git restore docs/SYNC_POLICY.md docs/NOTION_SCHEMA.md vault/templates/spec_template.md vault/templates/run_log_template.md`

## ログ保存先
- `vault/RUN/<YYYYMMDD_HHMM_SPEC-03_taskkey_spec>.md`

## 根拠
- `docs/SYNC_POLICY.md`
- `docs/NOTION_SCHEMA.md`

## 未決事項
- `####` の日次リセット方式（0001始まり固定か、全体連番か）。
