from pathlib import Path

from iksha.analysis.selector_usage import (
    SelectorUsage,
)
from iksha.analysis.selector_usage_result import (
    SelectorUsageResult,
)
from iksha.domain.file import File
from iksha.domain.states import UsageState


def make_file(tmp_path: Path, name: str) -> File:
    path = tmp_path / name

    return File(
        path=path,
        relative_path=name,
        file_type="css",
        size=0,
    )


def test_usages_for_returns_results_for_file(tmp_path: Path):
    css_file = make_file(tmp_path, "style.css")

    usage = SelectorUsage(
        selector=".card",
        state=UsageState.DEFINITELY_USED,
    )

    result = SelectorUsageResult(
        by_file={
            css_file: (usage,),
        }
    )

    assert result.usages_for(css_file) == (usage,)


def test_usages_for_returns_empty_tuple_for_unknown_file(
    tmp_path: Path,
):
    css_file = make_file(tmp_path, "style.css")
    other_file = make_file(tmp_path, "other.css")

    result = SelectorUsageResult(
        by_file={
            css_file: (),
        }
    )

    assert result.usages_for(other_file) == ()