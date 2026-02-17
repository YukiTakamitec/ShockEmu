# Vault README

## 目的
- Obsidian Vault を GitHub で管理し、仕様・実行ログ・参照資料を一元化する。

## フォルダ構成
- `vault/SPEC/`: Codex が作る作業指示（契約書）
- `vault/RUN/`: Claude Code の実行ログ（監査証跡）
- `vault/templates/`: SPEC/RUN テンプレート
- `vault/references/`: 参考資料

## 運用手順
1. 要件発生時、Codex が `vault/SPEC/` に SPEC を作成。
2. Claude Code が SPEC 準拠で実装・検証。
3. Claude Code が `vault/RUN/` にログを保存。
4. PR で CI（markdownlint + link check）を通す。

## SPEC運用ルール
- 1タスク=1SPEC。
- 変更範囲は `OK/NG` をディレクトリ単位で明記。
- 受入基準は必ずコマンド検証可能な形にする。

## RUN運用ルール
- 1実行=1RUNログ。
- 必須項目: 実行日時、コマンド、テスト結果、変更ファイル、理由、リスク、次アクション。

## 注意
- テストコマンド不明時は探索結果と暫定提案を分離し、勝手に導入しない。
- SPEC外変更は禁止。

なぜ: 変更の根拠と結果を後追い可能にし、運用の再現性を上げるため。
