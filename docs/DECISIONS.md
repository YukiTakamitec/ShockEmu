# Decisions

## 2026-02-19 確定事項
1. Knowledge 索引更新SLA
- 決定: 標準は `24時間以内`、クリティカル案件は `当日中`。

2. Event2/Event3 自動化の優先順位
- 決定: 優先1は Event3（Task.Execution State 更新）、優先2は Event2（Knowledge 更新）。

3. Event1 live retry/backoff 定数
- 決定: `max_retries=3`, `backoff_base_sec=1.0`, `backoff_factor=2.0` を標準値にする。

## 2026-02-19 追加確定事項
1. Notion API と MCP の採用優先
- 決定: 初期実装は Notion API 直接連携を優先し、MCP は置換可能な将来経路として保持する。

2. GitHub Issue/PR と Notion Task の一意キー
- 決定: 主キーは `TaskKey(Task ID)`、Issue/PR番号は外部参照IDとして扱う。

3. Knowledge の同期粒度
- 決定: `SPEC/RUN` 単位を正本とし、PRは関連リンクとして索引に紐付ける。

4. GWS の対象範囲
- 決定: 初期フェーズは Chat 通知のみ、Docs/Calendar は次フェーズ。

5. Figma 成果物の正本化方式
- 決定: `.fig` バイナリは保管しない。Figma URL + export成果物を正本運用。

6. Secret scan ルールの厳密度
- 決定: 高信頼シグネチャは hard fail、疑陽性は allowlist + 期限付き例外で管理。

7. 大容量ファイル制限値
- 決定: 単ファイル 10MB 超は失敗（例外なし）。

8. Notion例外（本文正本）承認フロー
- 決定: 承認者は Repo Owner + Reviewer の2者、承認理由と期限を RUN に記録。

9. Secret scan 対象範囲
- 決定: リポ全体走査を標準化し、除外は `node_modules/`, `.git/`, 生成物キャッシュのみ。

10. Secret allowlist 運用
- 決定: 2者承認必須、例外期限は30日、延長は再承認必須。

11. Link check 方針
- 決定: 内部リンク hard fail を維持。外部リンクは warning を維持し、四半期ごとに失敗率をレビュー。

12. サイズ例外ポリシー
- 決定: 特例を許可しない。大容量成果物は分割または外部ストレージ参照で対応。
