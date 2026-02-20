# Live State Policy

## Purpose
- Prevent duplicate Issue creation in Event1 when GitHub search indexing is delayed.
- Keep an auditable local idempotency cache.

## Target
- `tools/notion_sync/.live_state.json`
- Produced by `tools/notion_sync/event1_sync.py --mode live`

## Rules
1. Do not commit `.live_state.json` to Git.
2. Keep one cache per environment (local/CI runner) and rotate periodically.
3. On mismatch (Issue deleted/404), the script removes stale mapping automatically.
4. For long-lived environments, back up cache daily if running continuous sync jobs.

## Recommended Ops
- Warm-up verification:
```bash
python3 tools/notion_sync/event1_sync.py \
  --mode live \
  --event tools/notion_sync/examples/event_with_taskkey.json \
  --live-state tools/notion_sync/.live_state.json
```

- Reset cache (when re-seeding idempotency):
```bash
rm -f tools/notion_sync/.live_state.json
```

## Risks
- Cache is local-state; multi-runner deployments require shared state or strict sharding.
- If cache is lost, fallback depends on GitHub label search/list consistency.

## Token Hygiene
- If a Notion token is exposed in chat/logs/shell history, rotate it immediately.
- Revoke old token in Notion Integrations after issuing a new one.
- Re-run:
```bash
tools/notion_sync/verify_live_event23.sh
```
