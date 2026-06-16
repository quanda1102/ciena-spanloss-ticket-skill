# Eval Spec: ciena-spanloss-ticket-skill

Loss function for the Ciena span-loss ticket workflow. Golden cases use
`--mock` so evals run without live Ciena credentials.

## Criteria

1. **valid-json** — pipeline output parses as JSON.
2. **has-spanloss** — measured `measurements.spanloss_db` is numeric.
3. **severity-matches-delta** — ticket severity aligns with EOL delta rules.

## Golden cases

- **case-1** — EDFA link within EOL (`within_eol`).
- **case-2** — EDFA link minor exceed (`minor_over_eol`, Major ticket).
- **case-3** — RAMAN link major exceed (`major_over_eol`, Critical ticket).

## Spec

```json
{
  "skill": "ciena-spanloss-ticket-skill",
  "run": "python3 scripts/run_pipeline.py --alarm {input} --logic-table assets/logic_links_sample.csv --output {output} --mock",
  "criteria": [
    {"id": "valid-json", "text": "Output parses as JSON", "type": "command", "cmd": "python3 -c \"import json,sys; json.load(open(sys.argv[1]))\" {output}"},
    {"id": "has-spanloss", "text": "spanloss_db is numeric", "type": "command", "cmd": "python3 -c \"import json,sys; d=json.load(open(sys.argv[1])); assert isinstance(d['measurements']['spanloss_db'], (int,float))\" {output}"},
    {"id": "severity-matches-delta", "text": "Severity follows EOL delta threshold", "type": "command", "cmd": "python3 -c \"import json,sys; d=json.load(open(sys.argv[1])); a=d['assessment']; delta=a['delta_over_eol_db']; sev=a['severity']; assert (delta<=0 and sev=='info') or (0<delta<6 and sev=='major') or (delta>=6 and sev=='critical')\" {output}"}
  ],
  "golden": [
    {"id": "case-1", "input": "golden/case-1/input.json", "expected": null, "split": "val", "expected_status": "pending-first-green"},
    {"id": "case-2", "input": "golden/case-2/input.json", "expected": null, "split": "val", "expected_status": "pending-first-green"},
    {"id": "case-3", "input": "golden/case-3/input.json", "expected": null, "split": "val", "expected_status": "pending-first-green"}
  ]
}
```
