#!/usr/bin/env python3
"""Map Rx coordinates to logic link records from the trunk link table."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from parse_alarm import ParsedAlarm, component_to_rx_coordinate


REQUIRED_COLUMNS = {
    "device_rx",
    "coord_rx",
    "device_tx",
    "coord_tx",
    "eol_db",
    "link_type",
}


@dataclass
class LogicLink:
    """One row from the trunk logic link table."""

    link_id: str
    device_rx: str
    coord_rx: str
    device_tx: str
    coord_tx: str
    eol_db: float
    link_type: str
    trunk_name: str = ""

    @property
    def link_logic(self) -> str:
        return f"{self.device_tx} {self.coord_tx} <-> {self.device_rx} {self.coord_rx}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"link_logic": self.link_logic}


def _normalize_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def load_logic_links(path: Path) -> list[LogicLink]:
    """Load logic links from CSV."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"Logic link table is empty: {path}")
        field_map = {_normalize_header(name): name for name in reader.fieldnames}
        missing = REQUIRED_COLUMNS - set(field_map)
        if missing:
            raise ValueError(f"Logic link table missing columns: {sorted(missing)}")

        links: list[LogicLink] = []
        for index, row in enumerate(reader, start=2):
            try:
                links.append(
                    LogicLink(
                        link_id=str(row.get(field_map.get("link_id", ""), "") or f"row-{index}"),
                        device_rx=row[field_map["device_rx"]].strip().upper(),
                        coord_rx=row[field_map["coord_rx"]].strip(),
                        device_tx=row[field_map["device_tx"]].strip().upper(),
                        coord_tx=row[field_map["coord_tx"]].strip(),
                        eol_db=float(row[field_map["eol_db"]]),
                        link_type=row[field_map["link_type"]].strip().upper(),
                        trunk_name=str(row.get(field_map.get("trunk_name", ""), "") or "").strip(),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Invalid logic link row {index}: {exc}") from exc
        return links


def find_link_for_alarm(
    alarm: ParsedAlarm,
    links: list[LogicLink],
    rx_port: int = 8,
) -> tuple[str, LogicLink]:
    """Resolve Rx coordinate and return matching logic link."""
    coord_rx = component_to_rx_coordinate(alarm.component, rx_port=rx_port)
    device_rx = alarm.device_code.upper()
    for link in links:
        if link.device_rx == device_rx and link.coord_rx == coord_rx:
            return coord_rx, link
    raise ValueError(
        f"No logic link found for Rx endpoint {device_rx} {coord_rx}. "
        "Update the trunk logic table on NOCPRO."
    )


def map_alarm_to_link(alarm: ParsedAlarm, logic_table: Path, rx_port: int = 8) -> dict[str, Any]:
    """Return mapping payload used by downstream Ciena queries."""
    links = load_logic_links(logic_table)
    coord_rx, link = find_link_for_alarm(alarm, links, rx_port=rx_port)
    return {
        "coord_rx": coord_rx,
        "endpoint_rx": f"{alarm.device_code} {coord_rx}",
        "endpoint_tx": f"{link.device_tx} {link.coord_tx}",
        "link": link.to_dict(),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Map alarm to trunk logic link.")
    parser.add_argument("--alarm", required=True, help="Parsed alarm JSON.")
    parser.add_argument("--logic-table", required=True, help="Logic link CSV.")
    parser.add_argument("--output", help="Optional output JSON path.")
    args = parser.parse_args()
    alarm = ParsedAlarm(**json.loads(Path(args.alarm).read_text(encoding="utf-8")))
    result = map_alarm_to_link(alarm, Path(args.logic_table))
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
