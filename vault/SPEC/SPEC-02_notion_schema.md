# SPEC: SPEC-02 Notion schema

## 目的
- Notion DB（Projects/Tasks/Knowledge）の項目仕様を確定し、SoT責務を破綻させない。
- Notion実体の作成前に、GitHub側で項目定義と運用ルールを文書化する。

## 変更範囲（ディレクトリ単位）
### OK
- `docs/`
- `vault/knowledge/`（スキーマ説明やサンプル記録）

### NG
- `.github/workflows/`（本SPECでは対象外）
- 同期実装コード
- Notion本番DBの直接変更（本SPECでは文書化のみ）

## 手順
1. `docs/NOTION_SCHEMA.md` で Projects/Tasks/Knowledge のプロパティを定義する。
2. `Knowledge` の必須プロパティ（Record Type, GitHub Canonical Link, Summary, Status, Owner, Last Sync）を固定する。
3. Deliverable の Canonical Link 必須ルールを明記する。
4. FAQ/軽メモの例外時に `ExceptionApprovedBy` 必須であることを追記する。

## 受入基準（コマンドで検証可能）
1. 3DB（Projects/Tasks/Knowledge）の定義が存在すること。
- コマンド: `rg -n "Database: Projects|Database: Tasks|Database: Knowledge" docs/NOTION_SCHEMA.md`
- 期待結果: 3つの見出しがヒットする。

2. Knowledge必須項目が定義されていること。
- コマンド: `rg -n "Record Type|GitHub Canonical Link|Summary|Status|Owner|Last Sync" docs/NOTION_SCHEMA.md`
- 期待結果: 必須項目6つがヒットする。

3. 例外承認（ExceptionApprovedBy）が明文化されていること。
- コマンド: `rg -n "ExceptionApprovedBy|FAQ|軽メモ|例外" docs/NOTION_SCHEMA.md docs/CONSTITUTION.md`
- 期待結果: 例外条件と承認必須の記述がヒットする。

## 生成物
- `docs/NOTION_SCHEMA.md`（更新）
- 必要に応じて `vault/knowledge/notion_schema_notes.md`（任意）

## ロールバック
1. スキーマ文書のみ戻す。
- コマンド: `git restore docs/NOTION_SCHEMA.md`

## ログ保存先
- `vault/RUN/<YYYYMMDD_HHMM_SPEC-02_notion_schema>.md`

## 根拠
- `docs/CONSTITUTION.md`
- `docs/SYNC_POLICY.md`

## 未決事項
- Notion側で `ExceptionApprovedBy` を person にするか text にするか。
