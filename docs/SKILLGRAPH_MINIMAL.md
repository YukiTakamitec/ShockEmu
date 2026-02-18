# SkillGraph Minimal Design

## 目的
- Obsidian 上でスキルをグラフ化し、`SKILL.md` を短く再利用可能に保つ。
- 1ノード1責務で、実行時のトークン消費を抑える。

## 設計原則（省トークン）
1. 1 skill = 1 outcome
- 1つのスキルは1つの成果だけを返す。

2. 固定骨格 + 可変最小
- Frontmatter と 5セクションだけを使う。
- 長文説明は禁止し、根拠は参照リンクへ逃がす。

3. Execute-Now 形式
- 実行条件と最初の1手を明示する。
- 迷った時の分岐は最大3つまで。

4. 契約ベース
- `inputs/outputs/acceptance/evidence/constraints` を必須にする。

5. グラフ連携
- 各 skill に `upstream/downstream` を持たせる。
- Obsidian ではリンクで依存を可視化する。

## 推奨ノード（現行運用）
- `ORCH-00`: ルーティング
- `RES-01`: 調査
- `DOC-01`: 文書正規化
- `QA-01`: 品質ゲート
- `DES-01`: デザイン資産連携
- `OPS-01`: 同期運用

## Obsidian 運用
- `vault/knowledge/skill_graph.md` をインデックスにする。
- 各スキルは `[[skill:<id>]]` 形式で相互リンク。
- RUN には「使ったスキルID」だけ記録し、説明は書かない。

## 参考
- X: `https://x.com/arscontexta/status/2023957499183829467`
- Repo: `https://github.com/agenticnotetaking/arscontexta`

