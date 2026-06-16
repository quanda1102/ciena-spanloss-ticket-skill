# Trunk Logic Link Table

Maintain this table on NOCPRO (static + dynamic columns). The skill reads the static mapping CSV at runtime.

## Required columns

| Column | Description | Example |
|---|---|---|
| `link_id` | Unique row ID | `TD-001` |
| `trunk_name` | Trunk label | `Truc-1C-North` |
| `device_tx` | Transmit NE code | `HNI9104DWB71` |
| `coord_tx` | Tx port coordinate | `1-2-5` |
| `device_rx` | Receive NE code | `PDL9104DWB71` |
| `coord_rx` | Rx port coordinate | `1-2-8` |
| `eol_db` | End-of-life span-loss threshold (dB) | `25` |
| `link_type` | `EDFA` or `RAMAN` | `EDFA` |

## Lookup rule

Given a parsed alarm:

1. Normalize Rx coordinate from alarm component (default port 8).
2. Match `device_rx` + `coord_rx` in the table.
3. Return Tx endpoint, EOL, and link type for Ciena API queries.

## Dynamic columns (NOCPRO UI)

These are updated after each run and are not required in the CSV input:

- `tx_dbm`, `rx_dbm`, `spanloss_db`
- `delta_over_eol_db`
- `note`, `last_checked_at`

## Sample row

```csv
link_id,trunk_name,device_tx,coord_tx,device_rx,coord_rx,eol_db,link_type
TD-001,Truc-1C-North,HNI9104DWB71,1-2-5,PDL9104DWB71,1-2-8,25,EDFA
```

Export the trunk logic table daily (or on change) and pass it to the pipeline with `--logic-table`.
