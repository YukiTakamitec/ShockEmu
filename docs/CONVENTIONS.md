# Conventions

## 目的
- GitHub 上の Vault を唯一の Source of Truth とし、Codex と Claude Code の役割混線を防ぐ。
- SPEC を契約、RUN を監査ログとして固定し、変更の再現性とレビュー容易性を上げる。

## 役割分離
- Codex（統括）: 要件整理、`/vault/SPEC/` の作成、差分レビュー、受入判定。
- Claude Code（実行）: SPEC 準拠で編集と検証を実行し、`/vault/RUN/` に結果を記録。
- GitHub Actions（自動ゲート）: Markdown 品質とリンク健全性の早期検知。

なぜ: 誰が何を決めたかを分離しないと、変更理由が追えず再発防止ができないため。

## ディレクトリ規約
- `vault/`: Obsidian Vault 本体
- `vault/SPEC/`: 1タスク=1SPEC
- `vault/RUN/`: 1実行=1ログ
- `vault/templates/`: SPEC/RUN テンプレート
- `vault/references/`: 参照資料
- `agents/`: エージェント manifest
- `prompts/`: 固定プロンプト
- `.github/workflows/`: ドキュメント品質ゲート
- `docs/`: 運用規約

## 更新フロー
1. Codex が `vault/SPEC/` にタスク仕様を作成。
2. Claude Code が SPEC を読み、指定範囲のみ変更。
3. Claude Code がコマンド検証を実行。
4. Claude Code が `vault/RUN/` に実行ログを保存。
5. PR で CI 通過後にマージ。

なぜ: 仕様->実行->証跡を1本化すると、レビューが差分とログで閉じるため。

## 命名規則
- SPEC: `vault/SPEC/NN_task_slug.md`（例: `10_task_001.md`）
- RUN: `vault/RUN/YYYYMMDD_HHMM_task_slug.md`
- Agent: `agents/<ID>.yml`（例: `ECA-01.yml`）

## 禁止事項
- SPEC 未記載の変更。
- `vault/RUN/` 未記録での完了報告。
- 根拠なしの断定（探索結果と提案を混同しない）。
- 巨大ログ・巨大成果物の直接コミット。

## 変更範囲ルール
- SPEC に `OK/NG` をディレクトリ単位で必須記載。
- NG 範囲に触れる必要が出た場合は、実装せず差戻し質問を行う。

## RUNログ容量ルール
- 1ファイル目安: 300行以下。
- 1ファイルサイズ目安: 200KB以下（超過時は分割し、関連ログを相互参照する）。
- コマンド出力は要約優先、必要最小限のみ抜粋。
- 添付が必要な長文出力は別ファイル化し参照パスを記録。

なぜ: Vault の可読性低下とレビュー遅延を防ぐため。
