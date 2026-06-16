---
name: ciena-spanloss-ticket-skill
description: >-
  Automates daily NOCPRO span-loss alarm handling for Ciena optical transport:
  parse High Received Span loss alarms, map Rx coordinates via trunk logic link
  table, query Ciena MCP PM API for Tx/Rx or SPANLOSS (EDFA/RAMAN), compare
  against EOL threshold, enrich alarm fields, and generate Major or Critical
  maintenance tickets. Activates for suy hao, span loss, Ciena ticket, NOCPRO
  alarm enrichment, fiber attenuation assessment, optical trunk monitoring.
license: MIT
metadata:
  author: agent-skill-creator
  version: 1.0.0
  created: 2026-06-16
  last_reviewed: 2026-06-16
  review_interval_days: 90
  dependencies:
    - url: https://10.56.111.6/tron/api/v1/tokens
      name: Ciena TRON Token API
      type: api
    - url: https://10.56.111.6/tron/api/v1/pm/metrics/search
      name: Ciena PM Metrics API
      type: api
  schema_expectations:
    - url: https://10.56.111.6/tron/api/v1/tokens
      method: POST
      expected_keys:
        - token
        - expiresAt
    - url: https://10.56.111.6/tron/api/v1/pm/metrics/search
      method: POST
      expected_keys:
        - data
---

# /ciena-spanloss-ticket — Span Loss Assessment & Ticket Generation

You automate the daily NOCPRO → Ciena span-loss workflow on trunk network 1C:
receive alarm, resolve logic link, query live PM data, compare EOL, enrich the
alarm, and draft the correct ticket severity.

## Trigger

User invokes `/ciena-spanloss-ticket` followed by their input:

```
/ciena-spanloss-ticket Process today's High Received Span loss alarms
/ciena-spanloss-ticket Evaluate this NOCPRO alarm and create ticket
/ciena-spanloss-ticket Run span-loss check for PDL9104DWB71 LIM-1-2
/ciena-spanloss-ticket Đánh giá suy hao và sinh ticket Ciena
```

Also activates on: suy hao cáp, span loss EOL, làm giàu cảnh báo NOCPRO, Ciena PM API.

## Daily workflow

```
NOCPRO alarm → parse device + card → map Rx (port 8) → logic link table
→ Ciena token → PM query (EDFA: Tx/Rx, RAMAN: SPANLOSS)
→ spanloss vs EOL → enrich alarm → Major/Critical ticket
```

### Classification rules

| Condition | Status | Ticket |
|---|---|---|
| `spanloss - EOL ≤ 0` | Within EOL | Enrich only |
| `0 < spanloss - EOL < 6 dB` | Minor exceed | **Major** + CR for planned maintenance |
| `spanloss - EOL ≥ 6 dB` | Major exceed | **Critical** — dispatch immediately |

Threshold is configurable via `SPANLOSS_THRESHOLD_DB` (default `6`). Each network
region may use a different value — confirm with NOC operations.

## One-command pipeline

```bash
python3 scripts/run_pipeline.py \
  --alarm <alarm.json> \
  --logic-table <logic_links.csv> \
  --output result.json
```

**Live Ciena API** — set credentials first:

```bash
Set `CIENA_PASSWORD` in your shell environment before running live mode.
export CIENA_BASE_URL='https://10.56.111.6'
python3 scripts/run_pipeline.py \
  --alarm assets/alarm_sample.json \
  --logic-table assets/logic_links_sample.csv \
  --output result.json
```

**Offline / dry-run** (no Ciena network required):

```bash
python3 scripts/run_pipeline.py \
  --alarm assets/alarm_sample.json \
  --logic-table assets/logic_links_sample.csv \
  --output result.json \
  --mock --mock-scenario minor_over_eol
```

## Agent procedure (batch daily task)

1. **Collect alarms** — export new NOCPRO span-loss alarms (JSON or CSV).
2. **Refresh logic table** — export trunk logic link CSV from NOCPRO.
3. **Run pipeline** per alarm (or loop in a shell script).
4. **Post enriched fields** back to NOCPRO alarm record.
5. **Create ticket** when `ticket` object is non-null:
   - `major` → planned span-loss maintenance CR
   - `critical` → immediate cable fault handling
6. **Log failures** — missing logic link rows, API timeouts, incomplete PM bins.

## Output shape

```json
{
  "alarm": { "...": "..." },
  "mapping": { "endpoint_tx": "...", "endpoint_rx": "...", "link": { "...": "..." } },
  "measurements": { "tx_dbm": 2.0, "rx_dbm": -20.0, "spanloss_db": 22.0 },
  "assessment": {
    "delta_over_eol_db": -3.0,
    "severity": "info",
    "ticket_required": false
  },
  "enriched_alarm_fields": {
    "Link logic": "HNI9104DWB71 1-2-5 <-> PDL9104DWB71 1-2-8",
    "Spanloss": 22.0,
    "Đánh giá Span Loss": "Trong ngưỡng EOL"
  },
  "ticket": null
}
```

## Step scripts (isolated testing)

| Script | Purpose |
|---|---|
| `scripts/parse_alarm.py` | Parse NOCPRO alarm JSON |
| `scripts/map_link.py` | Resolve trunk logic link |
| `scripts/ciena_client.py` | Token + PM API client |
| `scripts/evaluate.py` | EOL comparison + ticket class |
| `scripts/run_pipeline.py` | **Run this** — full pipeline |

## References (load on demand)

- `references/nocpro-alarm-format.md` — alarm parsing rules
- `references/link-logic-table.md` — trunk table schema
- `references/api-reference.md` — Ciena TRON API details

## Failure modes

| Error | Action |
|---|---|
| Logic link not found | Add row to trunk table on NOCPRO, re-export CSV |
| `CIENA_PASSWORD` unset | Export env var or use `--mock` |
| PM bin empty / non-COMPL | Widen time range or retry after next 15-min bin |
| SSL errors on internal IP | Set `CIENA_VERIFY_SSL=false` (default) |

## Eval regression

```bash
python3 scripts/run_evals.py --validate
python3 scripts/run_evals.py --rollout
```

Optimize with autoresearch-universal using the bundled `evals/ciena-spanloss-ticket-skill.eval.md`.
