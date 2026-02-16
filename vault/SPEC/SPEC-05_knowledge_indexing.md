# SPEC: SPEC-05 Knowledge運用（SPEC/RUN索引）

## 目的
- Knowledge正本を `SPEC/RUN` 単位で管理し、Notionは索引として運用する。
- 初期は手動運用で確実性を優先し、将来自動化ポイントを明記する。

## 変更範囲（ディレクトリ単位）
### OK
- `docs/`
- `vault/templates/`
- `vault/knowledge/`

### NG
- Notion自動同期コード実装
- PRイベント自動登録（次スプリント以降）

## 手順
1. `Knowledge` レコード作成手順を定義する（Record Type=SPEC/RUN中心）。
2. SPEC作成時・RUN作成時のNotion索引更新手順を手動手順として記述する。
3. PRはKnowledge本体ではなく関連リンクとして扱う運用に固定する。
4. 将来自動化ポイント（イベント2/3連携）を明記する。

## 受入基準（コマンドで検証可能）
1. SPEC/RUN単位正本の規則が明記されていること。
- コマンド: `rg -n "SPEC/RUN|Knowledge|索引|Canonical Link|PRは関連リンク" docs/NOTION_SCHEMA.md docs/SYNC_POLICY.md`
- 期待結果: 正本と索引の役割分離がヒットする。

2. 手動運用手順がテンプレ/文書で確認できること。
- コマンド: `rg -n "手動|更新手順|Last Sync|Summary" docs/SYNC_POLICY.md vault/templates/run_log_template.md`
- 期待結果: 手動運用手順または運用項目がヒットする。

3. 将来自動化ポイントが明記されていること。
- コマンド: `rg -n "将来|自動化|イベント2|イベント3" docs/SYNC_POLICY.md docs/DECISIONS.md`
- 期待結果: 自動化対象が明確に記載されている。

## 生成物
- `docs/SYNC_POLICY.md`（更新）
- `docs/NOTION_SCHEMA.md`（更新）
- `vault/knowledge/knowledge_ops_guide.md`（任意）

## ロールバック
1. 運用文書変更を戻す。
- コマンド: `git restore docs/SYNC_POLICY.md docs/NOTION_SCHEMA.md vault/knowledge/`

## ログ保存先
- `vault/RUN/<YYYYMMDD_HHMM_SPEC-05_knowledge_indexing>.md`

## 根拠
- `docs/NOTION_SCHEMA.md`
- `docs/SYNC_POLICY.md`

## 未決事項
- Knowledge索引更新のSLA（当日中か、24時間以内か）。
