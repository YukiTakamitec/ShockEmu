# Decisions To Be Made

## 未決論点（断言しない事項）
1. Notion API と MCP の採用優先
- 現時点: 両方想定。
- 決定が必要: 先行実装を API 直接連携にするか、MCP 経由に統一するか。

2. GitHub Issue/PR と Notion Task の一意キー
- 現時点: `Task ID` / `Issue number` 併用案。
- 決定が必要: 永続IDの主キー設計。

3. Knowledge の同期粒度
- 現時点: PR 単位で Knowledge 更新。
- 決定が必要: SPEC/RUN 単位での分割レコード運用を標準化するか。

4. GWS の対象範囲
- 現時点: Chat 通知、Docs サマリ、Calendar 期限を候補。
- 決定が必要: 初期フェーズでどこまで自動化するか。

5. Figma 成果物の正本化方式
- 現時点: Export 物を `assets/` 管理、設計正本は GitHub リンク。
- 決定が必要: `.fig` を保管するか、URL + export のみか。

6. Secret scan ルールの厳密度
- 現時点: 簡易スキャン。
- 決定が必要: ブロック条件と false positive の扱い。

7. 大容量ファイル制限値
- 現時点: 暫定で 10MB 超を失敗。
- 決定が必要: 運用実態に合わせた閾値。

8. Notion例外（本文正本）承認フロー
- 現時点: FAQ/軽メモを例外許可。
- 決定が必要: 承認者と監査方法。

9. Secret scan 対象範囲
- 現時点: `.env` / 秘密鍵 / 典型キー形式を hard fail 対象。
- 決定が必要: リポ全体走査に対する除外パスの最終ポリシー。

10. Secret allowlist 運用
- 現時点: `docs/security/secret_allowlist.yml` を想定。
- 決定が必要: 承認フローの厳密化（2者承認の例外有無）と期限延長条件。

11. Link check 方針
- 現時点: 内部リンクは hard fail、外部リンクは warning。
- 決定が必要: warning から hard fail へ移行する条件（失敗率・期間）。

12. サイズ例外ポリシー
- 現時点: 単ファイル10MB超の例外なし。
- 決定が必要: 特例を許可する場合の保管先・分割規則・承認手順。
