"""
Aggregated CSS selector usage results for IKSHA.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from iksha.analysis.selector_usage import SelectorUsage
from iksha.domain.file import File


@dataclass
class SelectorUsageResult:
    """Selector usage results grouped by authoritative CSS source file."""

    by_file: dict[File, tuple[SelectorUsage, ...]] = field(
        default_factory=dict
    )

    def usages_for(self, file: File) -> tuple[SelectorUsage, ...]:
        """Return selector usage results for one CSS file."""
        return self.by_file.get(file, ())