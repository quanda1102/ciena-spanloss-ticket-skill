# Ciena API Reference

## Server

- Default MCP host: `https://10.56.111.6`
- Override with `CIENA_BASE_URL`

## Authentication

```
POST /tron/api/v1/tokens
Content-Type: application/x-www-form-urlencoded

username=admin&tenant=master&password=$CIENA_PASSWORD
```

Response fields: `token`, `tenant`, `username`, `expiresAt` (token lifetime ~1 hour).

Environment variables:

| Variable | Purpose | Default |
|---|---|---|
| `CIENA_BASE_URL` | API base URL | `https://10.56.111.6` |
| `CIENA_USERNAME` | Login user | `admin` |
| `CIENA_PASSWORD` | Login password | *(required for live mode)* |
| `CIENA_TENANT` | Tenant | `master` |
| `CIENA_VERIFY_SSL` | Verify TLS cert | `false` |
| `SPANLOSS_THRESHOLD_DB` | Major vs Critical split | `6` |

## PM Metrics Search

```
POST /tron/api/v1/pm/metrics/search
Authorization: Bearer <token>
Content-Type: application/vnd.api+json
```

### EDFA links

Query Tx and Rx separately:

| Metric | parameterNative | facilityNameNative |
|---|---|---|
| Transmit power | `OPOUT-OTS` | Tx coordinate (e.g. `1-2-5`) |
| Receive power | `OPR-OTS` | Rx coordinate (e.g. `1-2-8`) |

Span loss formula: `spanloss_db = tx_dbm - rx_dbm` (both in dBm).

### RAMAN links

Query span loss directly:

| Metric | parameterNative | facilityNameNative |
|---|---|---|
| Span loss | `SPANLOSS` | `TELEMETRY-<tx_coord>` |

Example: Tx at `1-1-5` → `TELEMETRY-1-1-5`.

## Payload template

```json
{
  "data": {
    "attributes": {
      "filter": [
        "AND",
        ["=", "granularity", "15_MINUTE"],
        ["=", "networkElementName", "PDL9104DWB71"],
        ["=", "parameterNative", "OPR-OTS"],
        ["=", "facilityNameNative", "1-2-8"]
      ],
      "pageSize": 1,
      "range": {
        "type": "absolute",
        "startTime": "2026-05-22T15:00:00+07:00",
        "endTime": "2026-05-22T16:00:00+07:00"
      }
    }
  }
}
```

Use the latest `period` bin with `binStateNative=COMPL` and `condition=OK`.
