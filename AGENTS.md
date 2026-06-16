# Ciena Span Loss Ticket Skill

## Purpose

Automate daily evaluation of fiber span loss on Ciena optical transport trunks:
parse NOCPRO alarms, map coordinates through the logic link table, query Ciena
PM APIs, compare against EOL thresholds, enrich alarms, and generate Major or
Critical tickets.

## Activation

Use when the user mentions:

- Span loss / suy hao cáp / High Received Span loss
- NOCPRO alarm enrichment
- Ciena ticket generation for optical trunk faults
- Daily attenuation assessment on network 1C

Invoke as `/ciena-spanloss-ticket` followed by the task description.

## Quick start

```bash
python3 scripts/run_pipeline.py \
  --alarm <alarm.json> \
  --logic-table <logic_links.csv> \
  --output result.json
```

For offline testing, add `--mock`. For live API access, set `CIENA_PASSWORD`.

## Full instructions

See [SKILL.md](SKILL.md) for the complete workflow, classification rules, API
details, and failure handling.

## Key files

| Path | Role |
|---|---|
| `SKILL.md` | Full skill specification |
| `scripts/run_pipeline.py` | Single pipeline entry-point |
| `assets/logic_links_sample.csv` | Sample trunk logic table |
| `assets/alarm_sample.json` | Sample NOCPRO alarm |
| `references/` | API and table documentation |
| `evals/` | Regression spec |

## Environment

| Variable | Required (live) | Default |
|---|---|---|
| `CIENA_PASSWORD` | Yes | — |
| `CIENA_BASE_URL` | No | `https://10.56.111.6` |
| `CIENA_USERNAME` | No | `admin` |
| `SPANLOSS_THRESHOLD_DB` | No | `6` |
