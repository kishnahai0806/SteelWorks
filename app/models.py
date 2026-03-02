"""
Domain models for the operations analytics user story.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IssueFilterSelection:
    """
    Filter scope used by operations analytics queries.

    Attributes:
        calendar_week_id: Selected production week identifier.
        production_line_ids: Selected production line identifiers.
    """

    calendar_week_id: int
    production_line_ids: list[int]
