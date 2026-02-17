# PR Submission Template (Sprint Close)

## Summary
This PR closes the current sprint scope for filesystem-first operations with Notion SoT / GitHub record.

### Completed
- SPEC-04: Event1 (Notion -> GitHub Issue) dry-run executable flow
  - `create -> update` idempotency verified
  - missing `TaskKey` returns `error` and does not create
- SPEC-05: Manual knowledge indexing ops (SPEC/RUN as canonical, Notion as index)
- CI guardrail contract + implementation
  - hard-fail vs warning boundary
  - secret allowlist scaffold
  - file size guard + RUN size warning

## Key Files
- `tools/notion_sync/event1_dry_run.py`
- `tools/notion_sync/README.md`
- `tools/notion_sync/examples/event_with_taskkey.json`
- `tools/notion_sync/examples/event_missing_taskkey.json`
- `vault/SPEC/SPEC-04_notion_to_github_issue_sync.md`
- `vault/SPEC/SPEC-05_knowledge_indexing.md`
- `vault/knowledge/knowledge_ops_guide.md`
- `docs/CONSTITUTION.md`
- `docs/SYNC_POLICY.md`
- `docs/NOTION_SCHEMA.md`
- `.github/workflows/docs_quality.yml`

## Acceptance Evidence (RUN Logs)
- `vault/RUN/20260217_025754_SPEC-04_sync_event1.md`
- `vault/RUN/20260217_030200_SPEC-05_knowledge_indexing.md`

## Checklist
- [ ] SPEC-04 acceptance commands reproduced locally
- [ ] SPEC-05 acceptance commands reproduced locally
- [ ] No scope violation (no Event2/Event3 automation implementation)
- [ ] CI behavior matches contract:
  - [ ] hard fail: explicit secrets, file >10MB
  - [ ] warning: external link failure, minor markdownlint
- [ ] Notion/GitHub responsibility split unchanged

## Out of Scope
- Notion API live integration (beyond dry-run)
- MCP-based sync implementation
- Event2/Event3 automation

## Follow-up (Next Sprint)
1. Implement Event1 with real Notion API + GitHub API calls.
2. Harden TaskKey lifecycle (generation, uniqueness, migration handling).
3. Start Event2 automation (PR -> Knowledge index update).
