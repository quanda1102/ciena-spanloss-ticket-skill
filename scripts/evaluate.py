#!/usr/bin/env python3
"""Evaluate span loss against EOL and classify ticket severity."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any


DEFAULT_THRESHOLD_DB = 6.0


@dataclass
class SpanLossAssessment:
    spanloss_db: float
    eol_db: float
    delta_over_eol_db: float
    status: str
    severity: str
    action: str
    ticket_required: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_spanloss(
    spanloss_db: float,
    eol_db: float,
    *,
    threshold_db: float | None = None,
) -> SpanLossAssessment:
    """Compare measured span loss with EOL and return ticket classification."""
    threshold = threshold_db if threshold_db is not None else float(
        os.getenv("SPANLOSS_THRESHOLD_DB", str(DEFAULT_THRESHOLD_DB))
    )
    delta = round(spanloss_db - eol_db, 2)

    if delta <= 0:
        return SpanLossAssessment(
            spanloss_db=round(spanloss_db, 2),
            eol_db=eol_db,
            delta_over_eol_db=delta,
            status="within_eol",
            severity="info",
            action="Enrich alarm only; no maintenance ticket required.",
            ticket_required=False,
        )

    if delta < threshold:
        return SpanLossAssessment(
            spanloss_db=round(spanloss_db, 2),
            eol_db=eol_db,
            delta_over_eol_db=delta,
            status="minor_over_eol",
            severity="major",
            action="Create Major ticket and CR for planned span-loss maintenance.",
            ticket_required=True,
        )

    return SpanLossAssessment(
        spanloss_db=round(spanloss_db, 2),
        eol_db=eol_db,
        delta_over_eol_db=delta,
        status="major_over_eol",
        severity="critical",
        action="Create Critical ticket and dispatch immediate cable fault handling.",
        ticket_required=True,
    )


def build_enriched_fields(
    *,
    link_logic: str,
    tx_dbm: float | None,
    rx_dbm: float | None,
    spanloss_db: float,
    assessment: SpanLossAssessment,
) -> dict[str, Any]:
    """Fields appended to the NOCPRO alarm per operations runbook."""
    return {
        "Link logic": link_logic,
        "Tx": tx_dbm,
        "Rx": rx_dbm,
        "Spanloss": spanloss_db,
        "Đánh giá Span Loss": (
            f"Vượt ngưỡng EOL {assessment.delta_over_eol_db:+.2f} dB"
            if assessment.delta_over_eol_db > 0
            else "Trong ngưỡng EOL"
        ),
        "Ticket severity": assessment.severity,
        "Recommended action": assessment.action,
    }


def build_ticket_payload(
    *,
    alarm_id: str,
    assessment: SpanLossAssessment,
    enriched_fields: dict[str, Any],
) -> dict[str, Any] | None:
    if not assessment.ticket_required:
        return None
    return {
        "source_alarm_id": alarm_id,
        "priority": assessment.severity,
        "category": "span_loss",
        "title": (
            "Critical span loss — service impact"
            if assessment.severity == "critical"
            else "Major span loss — preventive maintenance"
        ),
        "description": assessment.action,
        "enriched_fields": enriched_fields,
    }
