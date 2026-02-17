# SPEC: SPEC-06 Guardrails

## 目的
- secret scan / サイズ制限 / 大容量運用をCIに反映し、事故を早期検知する。
- 閾値は暫定仕様（単ファイル10MB、RUNログ200KB目安）で開始し、段階導入にする。
- CIが「何を止め、何を止めないか」を契約として固定する。

## 変更範囲（ディレクトリ単位）
### OK
- `.github/workflows/`
- `docs/`
- `vault/templates/`

### NG
- 本格DLP導入
- 外部SaaS連携の本実装

## 手順
1. hard fail / warning の線引きを `docs/CONSTITUTION.md` に固定し、本SPECへ要約を記載する。
- hard fail: 明確なsecret（`.env` / 秘密鍵 / 典型キー形式）、単ファイル >10MB
- warning: 外部リンク切れ、軽微なmarkdownlint
2. `docs_quality.yml` を契約に合わせて更新する。
- 内部リンク: hard fail
- 外部リンク: warning（`continue-on-error: true`）
- markdownlint: warning（`continue-on-error: true`）
3. false positive 例外手続きを定義する。
- allowlist 保存先: `docs/security/secret_allowlist.yml`
- 必須項目: fingerprint / reason / approved_by / expires_at
- 承認者と期限（Owner + QA-01 / 30日）を明記する。
4. サイズ閾値を運用文書とCIに一致させる。
- 単ファイル10MB hard fail
- RUNログ200KB目安（超過時は分割）
- 10MB例外は原則なし（必要時は `docs/DECISIONS.md` で事前承認）
5. 動作検証（ダミー投入）手順を受入基準に追加する。

## 受入基準（コマンドで検証可能）
1. hard fail / warning 契約が文書化されていること。
- コマンド: `rg -n "hard fail|warning|外部リンク|markdownlint|10MB|\\.env|PRIVATE KEY|AKIA" docs/CONSTITUTION.md`
- 期待結果: 判定境界が明記されている。

2. false positive 例外手続きが手続き化されていること。
- コマンド: `test -f docs/security/secret_allowlist.yml && rg -n "allowlist|approved_by|expires_at|Owner|QA-01|30日" docs/CONSTITUTION.md docs/security/secret_allowlist.yml`
- 期待結果: 保存先・承認者・期限の記述が確認できる。

3. 10MB例外ルールが明記されていること（例外なし or 事前承認）。
- コマンド: `rg -n "10MB|例外|例外なし|DECISIONS" docs/CONSTITUTION.md docs/DECISIONS.md .github/workflows/docs_quality.yml`
- 期待結果: 閾値と例外方針が一致している。

4. secret dummy で hard fail すること（検証後削除）。
- コマンド: `tmp=.tmp_secret_test.pem; printf '-----BEGIN PRIVATE KEY-----\\nTEST\\n-----END PRIVATE KEY-----\\n' > \"$tmp\"; set +e; matches=$(rg -n --hidden --glob '!.git/*' --glob '!ShockEmu/**' '(BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16})' . || true); test -n \"$matches\"; rc=$?; rm -f \"$tmp\"; test $rc -eq 0`
- 期待結果: 検出され、secret hard fail 条件を満たすことを確認できる。

5. 外部リンク切れが warning 扱い（stopしない）であること。
- コマンド: `rg -n "link-check-external|continue-on-error: true|External link failures are warning-only" .github/workflows/docs_quality.yml`
- 期待結果: 外部リンクジョブが non-blocking で、ログ通知方針が記載されている。

6. 11MBダミーでサイズガード相当が fail になること（検証後削除）。
- コマンド: `tmp=.tmp_11mb.bin; mkfile -n 11m \"$tmp\" 2>/dev/null || dd if=/dev/zero of=\"$tmp\" bs=1m count=11 >/dev/null 2>&1; set +e; oversized=$(find . -type f -size +10M ! -path './.git/*' ! -path './ShockEmu/*'); test -n \"$oversized\"; rc=$?; rm -f \"$tmp\"; test $rc -eq 0`
- 期待結果: 10MB超が検出され、サイズ hard fail 条件を満たすことを確認できる。

7. RUNログ200KB目安が文書化されていること。
- コマンド: `rg -n "200KB|RUNログ|分割" docs/CONVENTION*.md docs/SYNC_POLICY.md vault/templates/run_log_template.md`
- 期待結果: RUNログ容量運用ルールがヒットする。

## 生成物
- `.github/workflows/docs_quality.yml`（更新）
- `docs/CONSTITUTION.md`（更新）
- `docs/security/secret_allowlist.yml`（新規）
- `docs/DECISIONS.md`（更新）
- `vault/templates/run_log_template.md`（更新）

## ロールバック
1. CI設定変更を戻す。
- コマンド: `git restore .github/workflows/docs_quality.yml`

2. 文書変更を戻す。
- コマンド: `git restore docs/CONSTITUTION.md docs/DECISIONS.md docs/security/secret_allowlist.yml docs/SYNC_POLICY.md vault/templates/run_log_template.md`

## ログ保存先
- `vault/RUN/<YYYYMMDD_HHMM_SPEC-06_guardrails>.md`

## 根拠
- `.github/workflows/docs_quality.yml`
- `docs/CONSTITUTION.md`
- `docs/DECISIONS.md`

## 未決事項
- secret scan 対象範囲（対象ディレクトリ/除外ディレクトリの最終確定）。
- allowlist 運用（fingerprint単位かpath単位か、期限延長条件）。
- link check 方針（外部リンクwarningをhard failへ移行する判定基準）。
- サイズ例外（10MB超の特例を今後認めるか、認める場合の承認フロー）。
