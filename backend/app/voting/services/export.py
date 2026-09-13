"""Export service for vote history — CSV and JSON export."""

from __future__ import annotations

import csv
import io
import json
from typing import Any


class ExportService:
    """Export vote history to CSV or JSON."""

    @staticmethod
    def to_json(events: list[dict[str, Any]]) -> str:
        """Export events to JSON string.

        Args:
            events: List of vote event dictionaries.

        Returns:
            JSON string.
        """
        return json.dumps({"events": events}, indent=2, default=str)

    @staticmethod
    def to_csv(events: list[dict[str, Any]]) -> str:
        """Export events to CSV string.

        Args:
            events: List of vote event dictionaries.

        Returns:
            CSV string.
        """
        if not events:
            return ""

        # Get field names from first event
        fieldnames = list(events[0].keys())

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(events)

        return output.getvalue()

    @staticmethod
    def to_ndjson(events: list[dict[str, Any]]) -> str:
        """Export events to NDJSON (newline-delimited JSON).

        Args:
            events: List of vote event dictionaries.

        Returns:
            NDJSON string.
        """
        lines = [json.dumps(event, default=str) for event in events]
        return "\n".join(lines)
