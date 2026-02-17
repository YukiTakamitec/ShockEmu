# Architecture

## 全体構成
1. Notion Layer（SoT）
- Projects / Tasks / Knowledge の運用DB。
- 優先度・期限・担当・意思決定の正本。

2. GitHub Layer（Record + Quality）
- `vault/` に SPEC/RUN/Knowledge/Deliverable を格納。
- PR、CI、差分、履歴の証跡を管理。

3. Execution Layer
- Codex: 仕様策定・レビュー。
- Claude Code: SPECに沿った編集・検証・RUN作成。

4. Integration Layer
- MCP/Notion API/GitHub API で同期イベントを処理。
- GWS/Figma/Obsidian は参照・入出力チャネルとして接続。

## データフロー
1. Notion -> GitHub
- Task/PJ メタデータを Issue/PR に反映（実行チケット化）。

2. GitHub -> Notion
- PR/CI/Merge/Deliverable 更新を Notion Knowledge/Tasks に反映。

3. 外部成果物
- 正本は `vault/deliverables/` 管理。
- Notion は Canonical Link と要約のみ保持。

## 同期責務の固定
- Notion only: Priority/Due/Owner/意思決定。
- GitHub only: PR状態/CI結果/RUN/差分/成果物版。
- 競合回避のため、同一フィールドを双方向更新しない。

## 品質ゲート
- Docs Quality Workflow:
  - markdownlint
  - link check
  - secret scan（簡易）
  - file size guard

## 可観測性
- RUN に実行日時、コマンド、差分、検証結果を保存。
- CI サマリで失敗理由と再現コマンドを残す。

## 拡張方針
- 将来 Slack 等を追加しても、SoT/Record の責務は変更しない。
- 新規連携は `mcp/servers.md` と `docs/SYNC_POLICY.md` の更新を先行する。
