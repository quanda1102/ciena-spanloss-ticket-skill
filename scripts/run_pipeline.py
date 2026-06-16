#!/usr/bin/env python3
"""Single entry-point: NOCPRO alarm -> Ciena PM -> span-loss ticket."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ciena_client import CienaClient, mock_powers
from evaluate import (
    build_enriched_fields,
    build_ticket_payload,
    classify_spanloss,
)
from map_link import map_alarm_to_link
from parse_alarm import load_alarm


def _compute_spanloss(
    *,
    link_type: str,
    eol_db: float,
    device_tx: str,
    coord_tx: str,
    device_rx: str,
    coord_rx: str,
    mock: bool,
    mock_scenario: str | None,
) -> dict[str, float | None]:
    if mock:
        mock_values = mock_powers(link_type, eol_db, scenario=mock_scenario)
        if link_type == "RAMAN":
            return {
                "tx_dbm": None,
                "rx_dbm": None,
                "spanloss_db": float(mock_values["spanloss_db"]),
            }
        tx_dbm = float(mock_values["tx_dbm"])
        rx_dbm = float(mock_values["rx_dbm"])
        return {
            "tx_dbm": tx_dbm,
            "rx_dbm": rx_dbm,
            "spanloss_db": round(tx_dbm - rx_dbm, 2),
        }

    client = CienaClient()
    if link_type == "RAMAN":
        spanloss_db = client.fetch_raman_spanloss(device_tx=device_tx, coord_tx=coord_tx)
        return {"tx_dbm": None, "rx_dbm": None, "spanloss_db": round(spanloss_db, 2)}

    powers = client.fetch_edfa_powers(
        device_tx=device_tx,
        coord_tx=coord_tx,
        device_rx=device_rx,
        coord_rx=coord_rx,
    )
    tx_dbm = float(powers["tx_dbm"])
    rx_dbm = float(powers["rx_dbm"])
    return {
        "tx_dbm": tx_dbm,
        "rx_dbm": rx_dbm,
        "spanloss_db": round(tx_dbm - rx_dbm, 2),
    }


def run_pipeline(
    alarm_path: Path,
    logic_table_path: Path,
    *,
    output_path: Path,
    mock: bool = False,
    mock_scenario: str | None = None,
    threshold_db: float | None = None,
    rx_port: int = 8,
) -> dict[str, Any]:
    alarm = load_alarm(alarm_path)
    alarm_payload = json.loads(alarm_path.read_text(encoding="utf-8"))
    mapping = map_alarm_to_link(alarm, logic_table_path, rx_port=rx_port)
    link = mapping["link"]
    resolved_mock_scenario = (
        mock_scenario
        or alarm_payload.get("mock_scenario")
        or "within_eol"
    )

    pm = _compute_spanloss(
        link_type=link["link_type"],
        eol_db=float(link["eol_db"]),
        device_tx=link["device_tx"],
        coord_tx=link["coord_tx"],
        device_rx=link["device_rx"],
        coord_rx=link["coord_rx"],
        mock=mock,
        mock_scenario=resolved_mock_scenario,
    )
    assessment = classify_spanloss(
        float(pm["spanloss_db"]),
        float(link["eol_db"]),
        threshold_db=threshold_db,
    )
    enriched = build_enriched_fields(
        link_logic=link["link_logic"],
        tx_dbm=pm["tx_dbm"],
        rx_dbm=pm["rx_dbm"],
        spanloss_db=float(pm["spanloss_db"]),
        assessment=assessment,
    )
    result: dict[str, Any] = {
        "alarm": alarm.to_dict(),
        "mapping": mapping,
        "measurements": pm,
        "assessment": assessment.to_dict(),
        "enriched_alarm_fields": enriched,
        "ticket": build_ticket_payload(
            alarm_id=alarm.alarm_id,
            assessment=assessment,
            enriched_fields=enriched,
        ),
        "mode": "mock" if mock else "live",
    }
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate span loss and generate ticket payload.")
    parser.add_argument("--alarm", required=True, help="NOCPRO alarm JSON file.")
    parser.add_argument("--logic-table", required=True, help="Trunk logic link CSV.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    parser.add_argument("--mock", action="store_true", help="Use deterministic mock PM values.")
    parser.add_argument(
        "--mock-scenario",
        choices=["within_eol", "minor_over_eol", "major_over_eol"],
        help="Mock scenario when --mock is set.",
    )
    parser.add_argument("--threshold-db", type=float, help="EOL exceed threshold (default 6 dB).")
    parser.add_argument("--rx-port", type=int, default=8, help="Default Rx port suffix.")
    args = parser.parse_args(argv)

    try:
        run_pipeline(
            Path(args.alarm),
            Path(args.logic_table),
            output_path=Path(args.output),
            mock=args.mock,
            mock_scenario=args.mock_scenario,
            threshold_db=args.threshold_db,
            rx_port=args.rx_port,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc), "error_type": type(exc).__name__}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
