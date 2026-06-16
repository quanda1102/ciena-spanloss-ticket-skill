#!/usr/bin/env python3
"""Ciena MCP API client for token auth and PM span-loss queries."""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


DEFAULT_BASE_URL = "https://10.56.111.6"
PM_METRICS_PATH = "/tron/api/v1/pm/metrics/search"
TOKEN_PATH = "/tron/api/v1/tokens"


@dataclass
class CienaConfig:
    base_url: str
    username: str
    password: str
    tenant: str = "master"
    verify_ssl: bool = False
    timeout_sec: int = 30

    @classmethod
    def from_env(cls) -> "CienaConfig":
        return cls(
            base_url=os.getenv("CIENA_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            username=os.getenv("CIENA_USERNAME", "admin"),
            password=os.getenv("CIENA_PASSWORD", ""),
            tenant=os.getenv("CIENA_TENANT", "master"),
            verify_ssl=os.getenv("CIENA_VERIFY_SSL", "false").lower() in {"1", "true", "yes"},
        )


class CienaClient:
    """Minimal Ciena TRON API wrapper for span-loss workflows."""

    def __init__(self, config: CienaConfig | None = None) -> None:
        self.config = config or CienaConfig.from_env()
        self._token: str | None = None

    def _ssl_context(self) -> ssl.SSLContext | None:
        if self.config.verify_ssl:
            return None
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> Any:
        url = f"{self.config.base_url}{path}"
        request = urllib.request.Request(url, data=body, method=method)
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.config.timeout_sec,
                context=self._ssl_context(),
            ) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ciena API {method} {path} failed ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ciena API unreachable at {url}: {exc}") from exc

    def get_token(self, force_refresh: bool = False) -> str:
        """Authenticate and cache bearer token (~1 hour lifetime)."""
        if self._token and not force_refresh:
            return self._token
        if not self.config.password:
            raise RuntimeError(
                "CIENA_PASSWORD is not set. Export credentials or run with --mock."
            )
        form = urllib.parse.urlencode(
            {
                "username": self.config.username,
                "tenant": self.config.tenant,
                "password": self.config.password,
            }
        ).encode("utf-8")
        payload = self._request(
            "POST",
            TOKEN_PATH,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            body=form,
        )
        token = payload.get("token")
        if not token:
            raise RuntimeError(f"Token response missing token field: {payload}")
        self._token = token
        return token

    def _time_range(self, hours: int = 1) -> dict[str, str]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=hours)
        return {
            "type": "absolute",
            "startTime": start.isoformat(timespec="seconds"),
            "endTime": end.isoformat(timespec="seconds"),
        }

    def _pm_payload(
        self,
        *,
        network_element: str,
        parameter_native: str,
        facility_name_native: str,
        hours: int = 1,
    ) -> dict[str, Any]:
        return {
            "data": {
                "attributes": {
                    "filter": [
                        "AND",
                        ["=", "granularity", "15_MINUTE"],
                        ["=", "networkElementName", network_element],
                        ["=", "parameterNative", parameter_native],
                        ["=", "facilityNameNative", facility_name_native],
                    ],
                    "pageSize": 1,
                    "range": self._time_range(hours=hours),
                }
            }
        }

    def _latest_pm_value(self, response: dict[str, Any]) -> float:
        records = response.get("data") or []
        if not records:
            raise RuntimeError(f"No PM data returned: {response}")
        period = records[0].get("attributes", {}).get("period") or {}
        if not period:
            values = records[0].get("attributes", {}).get("values") or {}
            period = values
        if not period:
            raise RuntimeError(f"PM record missing period/values: {records[0]}")
        latest_key = sorted(period.keys())[-1]
        value = period[latest_key].get("value")
        if value is None:
            raise RuntimeError(f"PM record missing value at {latest_key}: {period[latest_key]}")
        return float(value)

    def query_pm(
        self,
        *,
        network_element: str,
        parameter_native: str,
        facility_name_native: str,
        hours: int = 1,
    ) -> float:
        token = self.get_token()
        payload = self._pm_payload(
            network_element=network_element,
            parameter_native=parameter_native,
            facility_name_native=facility_name_native,
            hours=hours,
        )
        response = self._request(
            "POST",
            PM_METRICS_PATH,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/vnd.api+json",
            },
            body=json.dumps(payload).encode("utf-8"),
        )
        return self._latest_pm_value(response)

    def fetch_edfa_powers(
        self,
        *,
        device_tx: str,
        coord_tx: str,
        device_rx: str,
        coord_rx: str,
    ) -> dict[str, float]:
        tx_dbm = self.query_pm(
            network_element=device_tx,
            parameter_native="OPOUT-OTS",
            facility_name_native=coord_tx,
        )
        rx_dbm = self.query_pm(
            network_element=device_rx,
            parameter_native="OPR-OTS",
            facility_name_native=coord_rx,
        )
        return {"tx_dbm": tx_dbm, "rx_dbm": rx_dbm}

    def fetch_raman_spanloss(
        self,
        *,
        device_tx: str,
        coord_tx: str,
    ) -> float:
        facility = f"TELEMETRY-{coord_tx}"
        return self.query_pm(
            network_element=device_tx,
            parameter_native="SPANLOSS",
            facility_name_native=facility,
        )


def mock_powers(link_type: str, eol_db: float, scenario: str | None = None) -> dict[str, float]:
    """Deterministic mock PM values for offline testing."""
    if link_type == "RAMAN":
        presets = {
            "within_eol": eol_db - 2.5,
            "minor_over_eol": eol_db + 3.0,
            "major_over_eol": eol_db + 7.0,
        }
        spanloss = presets.get(scenario or "within_eol", eol_db - 2.5)
        return {"spanloss_db": round(spanloss, 2)}

    presets = {
        "within_eol": (2.0, -20.0),
        "minor_over_eol": (4.0, -24.0),
        "major_over_eol": (5.0, -32.0),
    }
    tx_dbm, rx_dbm = presets.get(scenario or "within_eol", (2.0, -20.0))
    return {"tx_dbm": tx_dbm, "rx_dbm": rx_dbm, "spanloss_db": round(tx_dbm - rx_dbm, 2)}
