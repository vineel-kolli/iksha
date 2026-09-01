from pathlib import Path

from iksha.dependency.php_resolver import PHPDependencyResolver
from iksha.domain.file import File
from iksha.domain.reference import ReferenceKind
from iksha.domain.source_location import SourceLocation
from iksha.parsing.result import Observation


def make_file(
    tmp_path: Path,
    relative_path: str,
) -> File:
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "<?php echo 'test'; ?>",
        encoding="utf-8",
    )

    return File(
        path=path,
        relative_path=relative_path,
        file_type="php",
        size=path.stat().st_size,
    )


def make_observation(
    source: File,
    expression: str,
) -> Observation:
    return Observation(
        source=source,
        kind=ReferenceKind.REQUIRE,
        value=expression,
        location=SourceLocation(
            line=1,
            column=1,
        ),
    )


def test_resolver_resolves_dir_expression(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "all-products.php",
    )

    target = make_file(
        tmp_path,
        "includes/search-engine.php",
    )

    resolver = PHPDependencyResolver(
        tmp_path,
    )

    resolver.index_files(
        [source, target]
    )

    observation = make_observation(
        source,
        "__DIR__ . '/includes/search-engine.php'",
    )

    result = resolver.resolve(
        observation
    )

    assert result.resolved is True
    assert result.target is target


def test_resolver_resolves_dir_expression_for_connect(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "search-suggest.php",
    )

    target = make_file(
        tmp_path,
        "connect.php",
    )

    resolver = PHPDependencyResolver(
        tmp_path,
    )

    resolver.index_files(
        [source, target]
    )

    observation = make_observation(
        source,
        "__DIR__ . '/connect.php'",
    )

    result = resolver.resolve(
        observation
    )

    assert result.resolved is True
    assert result.target is target


def test_resolver_preserves_authoritative_file(
    tmp_path: Path,
):
    source = make_file(
        tmp_path,
        "search-suggest.php",
    )

    target = make_file(
        tmp_path,
        "connect.php",
    )

    resolver = PHPDependencyResolver(
        tmp_path,
    )

    resolver.index_files(
        [source, target]
    )

    observation = make_observation(
        source,
        "__DIR__ . '/connect.php'",
    )

    result = resolver.resolve(
        observation
    )

    assert result.target is target
    assert result.target is resolver._files[
        target.path
    ]
