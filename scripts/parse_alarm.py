#!/usr/bin/env python3
"""Parse NOCPRO span-loss alarms into structured fields."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


CARD_PREFIXES = ("LIM", "SRA", "EDFA", "RAMAN", "OTU", "OPS", "OSC")


@dataclass
class ParsedAlarm:
    """Normalized fields extracted from a NOCPRO alarm."""

    alarm_id: str
    alarm_type: str
    device_code: str
    component: str
    raw_text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _coerce_alarm(payload: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(payload, str):
        return {"raw_text": payload}
    return dict(payload)


def extract_device_code(text: str) -> str:
    """Return the network element code (e.g. PDL9104DWB71)."""
    match = re.search(r"\b([A-Z]{3}\d{4}[A-Z0-9]+)\b", text)
    if not match:
        raise ValueError(f"Cannot find device code in alarm text: {text!r}")
    return match.group(1)


def extract_component(text: str) -> str:
    """Return card coordinate like LIM-1-2 from alarm text."""
    match = re.search(
        r"\b(?:" + "|".join(CARD_PREFIXES) + r")-(\d+-\d+)\b",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        prefix = match.group(0).split("-")[0].upper()
        return f"{prefix}-{match.group(1)}"
    match = re.search(r"\b(\d+-\d+-\d+)\b", text)
    if match:
        parts = match.group(1).split("-")
        return f"LIM-{parts[0]}-{parts[1]}"
    raise ValueError(f"Cannot find component coordinate in alarm text: {text!r}")


def component_to_rx_coordinate(component: str, rx_port: int = 8) -> str:
    """Strip card name and build Rx port coordinate (default port 8)."""
    normalized = component.upper().strip()
    if re.fullmatch(r"\d+-\d+-\d+", normalized):
        return normalized
    for prefix in CARD_PREFIXES:
        if normalized.startswith(prefix + "-"):
            shelf_slot = normalized[len(prefix) + 1 :]
            return f"{shelf_slot}-{rx_port}"
    if re.fullmatch(r"\d+-\d+", normalized):
        return f"{normalized}-{rx_port}"
    raise ValueError(f"Unsupported component format: {component!r}")


def parse_alarm(payload: dict[str, Any] | str) -> ParsedAlarm:
    """Parse alarm dict or free-text string into structured fields."""
    data = _coerce_alarm(payload)
    raw_text = (
        data.get("raw_text")
        or data.get("description")
        or data.get("alarm_text")
        or json.dumps(data, ensure_ascii=False)
    )
    device_code = data.get("device_code") or data.get("network_element") or extract_device_code(raw_text)
    component = data.get("component") or extract_component(raw_text)
    alarm_type = data.get("alarm_type") or data.get("type") or "High Received Span loss"
    alarm_id = str(data.get("alarm_id") or data.get("id") or f"{device_code}:{component}")
    return ParsedAlarm(
        alarm_id=alarm_id,
        alarm_type=alarm_type,
        device_code=device_code.upper(),
        component=component.upper(),
        raw_text=raw_text,
    )


def load_alarm(path: Path) -> ParsedAlarm:
    """Load alarm from JSON file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return parse_alarm(payload)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Parse a NOCPRO span-loss alarm.")
    parser.add_argument("--input", required=True, help="Alarm JSON file.")
    parser.add_argument("--output", help="Optional output JSON path.")
    args = parser.parse_args()
    result = load_alarm(Path(args.input)).to_dict()
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
