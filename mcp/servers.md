# MCP Servers Design

## Notion
- 用途: Projects/Tasks/Knowledge のメタ情報管理（SoT）
- 取得データ: Priority, Due, Owner, Status, Summary, Canonical Link
- 保存先: GitHub 側は `vault/SPEC/`, `vault/RUN/`, `vault/knowledge/` への参照情報
- 権限:
  - Read: Projects/Tasks/Knowledge
  - Write: Knowledge のリンク/要約、Task.Execution State（同期対象のみ）

## GWS (Google Workspace)
- 用途: 通知・共有（Chat/Docs/Calendar候補）
- 取得データ: 通知対象イベント、配布先設定
- 保存先: GitHub 正本（通知設定は docs/mcp）
- 権限:
  - Chat: 投稿権限
  - Docs: 追記権限（必要時）
  - Calendar: 予定作成/更新（必要時）

## Figma
- 用途: デザイン参照と出力物追跡
- 取得データ: ファイルURL、バージョン情報、エクスポート成果物
- 保存先: `assets/` と `vault/deliverables/`（正本リンク管理）
- 権限:
  - Read: ファイル参照
  - Export: 必要範囲のみ

## Obsidian
- 用途: Vault の編集UI
- 取得データ: ローカルMarkdown（Git管理）
- 保存先: `vault/`（GitHubで版管理）
- 権限:
  - ローカルファイル読み書き（Git運用前提）
