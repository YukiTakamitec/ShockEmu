# SPEC: SPEC-01 Repo bootstrap

## 目的
- Notion SoT / GitHub証跡・品質ゲート運用の土台を固定する。
- 1スプリントで必要なフォルダ、テンプレ、方針文書、CIガードレールを初期整備する。

## 変更範囲（ディレクトリ単位）
### OK
- `docs/`
- `vault/`
- `agents/`
- `prompts/`
- `mcp/`
- `.github/workflows/`

### NG
- `ShockEmu/`（ネスト複製領域）
- `.git/`
- アプリ実装コード（同期本実装）

## 手順
1. `docs/CONSTITUTION.md` に固定仕様と例外条件を明文化する。
2. `vault/templates/` のテンプレを整備し、SPEC/RUNの標準形式を固定する。
3. `prompts/` と `agents/` に役割分離の運用規約を作成する。
4. `.github/workflows/docs_quality.yml` を整備し、md/link/secret/size の最低ゲートを設定する。
5. ディレクトリ未追跡防止のため `.gitkeep` を追加する。

## 受入基準（コマンドで検証可能）
1. 必須ディレクトリ・ファイルが存在すること。
- コマンド: `find docs vault agents prompts mcp .github/workflows -maxdepth 3 -type f | sort`
- 期待結果: 主要ファイル（Constitution, templates, prompts, workflow）が列挙される。

2. 固定仕様と例外条件が明文化されていること。
- コマンド: `rg -n "SoT|GitHub|例外|FAQ|Canonical Link" docs/CONSTITUTION.md`
- 期待結果: 固定仕様5点と例外条件の記述行がヒットする。

3. CIに4ガード（md/link/secret/size）があること。
- コマンド: `rg -n "markdownlint|lychee|gitleaks|File Size Guard|10M" .github/workflows/docs_quality.yml`
- 期待結果: 4種類のジョブ/ルール定義がヒットする。

## 生成物
- `docs/CONSTITUTION.md`
- `docs/ARCHITECTURE.md`
- `docs/SYNC_POLICY.md`
- `vault/templates/*.md`
- `.github/workflows/docs_quality.yml`

## ロールバック
1. 変更を取り消す。
- コマンド: `git restore docs/ vault/ agents/ prompts/ mcp/ .github/workflows/`

2. 新規ファイルをまとめて取り消す（未コミット時）。
- コマンド: `git clean -fd docs vault agents prompts mcp .github/workflows`

## ログ保存先
- `vault/RUN/<YYYYMMDD_HHMM_SPEC-01_repo_bootstrap>.md`

## 根拠
- `docs/CONSTITUTION.md`
- `docs/ARCHITECTURE.md`
- `.github/workflows/docs_quality.yml`

## 未決事項
- CI閾値（10MB/200KB）の最終値は運用実績を見て見直す。
