# NOCPRO Alarm Format

## Typical alarm

NOCPRO pushes span-loss alarms such as **High Received Span loss**. The skill needs:

| Field | Source | Example |
|---|---|---|
| Device code | Network element name | `PDL9104DWB71` |
| Component | Card coordinate in alarm text | `LIM-1-2` |
| Alarm type | Alarm name | `High Received Span loss` |

## Rx coordinate normalization

Alarms usually report the card, not the Rx port. Standard rule:

1. Strip the card prefix (`LIM`, `SRA`, …).
2. Keep shelf-slot (`1-2`).
3. Append default Rx port `8`.

Example: `LIM-1-2` → Rx coordinate `1-2-8` on device `PDL9104DWB71`.

Full Rx endpoint: `PDL9104DWB71 1-2-8`.

## Input formats

### JSON (preferred)

```json
{
  "alarm_id": "NCP-20260522-001",
  "alarm_type": "High Received Span loss",
  "device_code": "PDL9104DWB71",
  "component": "LIM-1-2",
  "description": "High Received Span loss on PDL9104DWB71 LIM-1-2"
}
```

### Free text

The parser extracts device code and component via regex when structured fields are absent.

## Enriched output fields

After PM query and EOL comparison, append to the alarm:

| Field | Meaning |
|---|---|
| Link logic | Tx ↔ Rx logical link |
| Tx | Transmit power (dBm) |
| Rx | Receive power (dBm) |
| Spanloss | Measured span loss (dB) |
| Đánh giá Span Loss | Delta vs EOL threshold |
| Ticket severity | `info`, `major`, or `critical` |
| Recommended action | Operations next step |
