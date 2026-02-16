# SPEC: SPEC-06 Guardrails

## 目的
- secret scan / サイズ制限 / 大容量運用をCIに反映し、事故を早期検知する。
- 閾値は暫定仕様（単ファイル10MB、RUNログ200KB目安）で開始し、段階導入にする。

## 変更範囲（ディレクトリ単位）
### OK
- `.github/workflows/`
- `docs/`
- `vault/templates/`

### NG
- 本格DLP導入
- 外部SaaS連携の本実装

## 手順
1. `docs_quality.yml` に secret scan（明確な漏洩のみブロック）を設定する。
2. ファイルサイズガード（10MB）を有効化する。
3. RUNログ200KB目安を文書化し、超過時の分割ルールを定義する。
4. assets集約運用（提出画像のみGitHub保管）を明文化する。

## 受入基準（コマンドで検証可能）
1. CIに secret/size ガードが存在すること。
- コマンド: `rg -n "gitleaks|File Size Guard|10M|secret" .github/workflows/docs_quality.yml`
- 期待結果: secret scan と size guard の定義がヒットする。

2. RUNログ容量目安が文書化されていること。
- コマンド: `rg -n "200KB|RUNログ|分割" docs/CONVENTION*.md docs/SYNC_POLICY.md vault/templates/run_log_template.md`
- 期待結果: RUNログ容量運用ルールがヒットする。

3. assets運用ルールが明記されていること。
- コマンド: `rg -n "assets|提出物|Figma|URL正本|GitHub保管" docs/CONSTITUTION.md docs/DECISIONS.md mcp/servers.md`
- 期待結果: Figma/画像保管ルールがヒットする。

## 生成物
- `.github/workflows/docs_quality.yml`（更新）
- `docs/CONVENTIONS.md` or `docs/CONSTITUTION.md`（更新）
- `vault/templates/run_log_template.md`（更新）

## ロールバック
1. CI設定変更を戻す。
- コマンド: `git restore .github/workflows/docs_quality.yml`

2. 文書変更を戻す。
- コマンド: `git restore docs/CONSTITUTION.md docs/CONVENTIONS.md docs/SYNC_POLICY.md vault/templates/run_log_template.md`

## ログ保存先
- `vault/RUN/<YYYYMMDD_HHMM_SPEC-06_guardrails>.md`

## 根拠
- `.github/workflows/docs_quality.yml`
- `docs/CONSTITUTION.md`
- `docs/DECISIONS.md`

## 未決事項
- false positive の扱い（warning運用期間の長さ）。
