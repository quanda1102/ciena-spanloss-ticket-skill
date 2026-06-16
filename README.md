# ciena-spanloss-ticket-skill

Automates NOCPRO span-loss alarm handling on Ciena optical transport: parse
alarms, map trunk logic links, query Ciena PM API, compare EOL, enrich alarms,
and generate Major/Critical tickets.

## Install

### Auto-detect (recommended)

```bash
./install.sh
```

### Cursor (project-level)

```bash
./install.sh --platform cursor
# or
cp -R . /path/to/project/.cursor/skills/ciena-spanloss-ticket-skill
```

### Claude Code

```bash
./install.sh --platform claude
# or
cp -R . ~/.claude/skills/ciena-spanloss-ticket-skill
```

### Universal path

```bash
cp -R . ~/.agents/skills/ciena-spanloss-ticket-skill
```

## Use

Open a new agent session and type:

```
/ciena-spanloss-ticket Process today's span loss alarms
```

Or run the pipeline directly:

```bash
Set `CIENA_PASSWORD` in your shell environment before running live mode.
python3 scripts/run_pipeline.py \
  --alarm assets/alarm_sample.json \
  --logic-table assets/logic_links_sample.csv \
  --output result.json
```

## Test

```bash
python3 scripts/run_evals.py --validate
python3 scripts/run_evals.py --rollout
```

## Structure

```
ciena-spanloss-ticket-skill/
├── SKILL.md              # Skill definition
├── AGENTS.md             # Cross-platform companion
├── scripts/
│   ├── run_pipeline.py   # Main entry-point
│   ├── parse_alarm.py
│   ├── map_link.py
│   ├── ciena_client.py
│   ├── evaluate.py
│   └── run_evals.py
├── assets/               # Sample alarm + logic table
├── references/           # API & format docs
└── evals/                # Regression spec
```

## License

MIT
