# Sprint Plan (5-10 business days)

## 方針
- 1スプリントで「イベント1（Notion -> GitHub Issue同期）の確実稼働」を最優先にする。
- 全自動化は狙わず、仕様固定・雛形・検証手順を先に固める。

## 実行順と依存関係
1. `SPEC-01 Repo bootstrap`
- 依存: なし
- 成果: 運用土台（docs/templates/CI）

2. `SPEC-02 Notion schema`
- 依存: SPEC-01
- 成果: Projects/Tasks/Knowledge項目の固定

3. `SPEC-03 TaskKey仕様`
- 依存: SPEC-02
- 成果: `TSK-YYYYMMDD-####` と埋め込み規則

4. `SPEC-05 Knowledge運用`
- 依存: SPEC-02, SPEC-03
- 成果: SPEC/RUN正本 + Notion索引の手動運用

5. `SPEC-04 Notion→GitHub Issue同期（イベント1）`
- 依存: SPEC-02, SPEC-03
- 成果: API直結前提の最小雛形と動作確認手順

6. `SPEC-06 Guardrails`
- 依存: SPEC-01
- 成果: secret/size/RUN容量運用のCI反映

## クリティカルパス
- SPEC-01 -> SPEC-02 -> SPEC-03 -> SPEC-04

## マイルストーン
- M1（Day 1-2）: SPEC-01, 02 完了
- M2（Day 3-4）: SPEC-03, 05 完了
- M3（Day 5-7）: SPEC-04 完了（最重要）
- M4（Day 8-10）: SPEC-06 + 全体レビュー

## 完了条件
- 6つのSPECが `vault/SPEC/` に揃っている。
- 各SPECに検証可能な受入基準がある。
- Event 1 の最小運用（手順＋雛形＋検証）が実施可能。
- 未決事項は `docs/DECISIONS.md` または各SPECの未決事項に記載済み。
