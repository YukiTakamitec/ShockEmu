# Constitution

## 目的
- Notion SoT / GitHub 証跡・品質ゲート / 外部成果物 GitHub 正本の運用を安定させる。
- 役割と責務の衝突を防ぎ、変更の追跡可能性を担保する。

## 固定仕様（変更禁止）
1. System of Truth（SoT）は Notion。
- PJ/タスク/業務状態（Priority/Due/Owner/意思決定）は Notion が正。

2. 版管理・実行証跡・品質ゲートは GitHub が正。
- SPEC/RUN/差分/CI結果は GitHub が正。

3. 外部に出す成果物は GitHub 正本。
- 提出物の正本は GitHub の管理対象に置く。

4. Notion の役割は「最新へのリンク＋要約＋閲覧性」。
- Notion 単体で正本管理を行わない。

5. Notion 本文を正本にするのは例外。
- 軽いメモ、社内短文 FAQ などを例外として許容。
- 例外時も、可能なら GitHub Canonical Link を記録する。

## 例外条件（Notion正本を許す条件）
- 文字数が短く更新頻度が高い運用メモで、版管理コストが便益を上回る。
- 社内閲覧のみで、外部提出・監査証跡の対象外。
- 仕様・成果物・実行記録に影響しない補助情報。

例外禁止:
- 提出物本文、仕様本文、受入基準、実行ログ、審査結果の正本化。

## 役割分離
- Codex: 司令塔（設計、SPEC生成、差分レビュー、品質基準策定）
- Claude Code: 実行者（SPEC準拠で編集、検証、RUNログ作成）
- GitHub Actions: 品質ゲート（md lint/link/secret/サイズ）

## 真実の置き場
- 業務メタ（Priority/Due/Owner/意思決定）: Notion
- 実体ファイル（SPEC/RUN/Deliverable/差分）: GitHub

## 運用原則
- 同一フィールドを双方向同時更新しない。
- 不明点は断言しない。`docs/DECISIONS.md` に未決論点として記録する。
- ルール変更は必ずファイル差分で残す。
