"""Tests for the tests/conftest.py db_at_revision_* fixture machinery
(_db_pinned_to_revision) itself: several other test modules (e.g.
test_emergency_profile_canonical.py, test_protected_person_preflight.py) rely
on it to pin the shared test DB to a historical Alembic revision and always
restore HEAD afterwards, including when the test raises. This file proves
that restoration mechanism in isolation, rather than trusting it implicitly
via those modules.
"""

import pytest
import sqlalchemy as sa

from tests.conftest import _HEAD_REVISION, _current_revision, _db_pinned_to_revision

pytestmark = pytest.mark.migration


def test_db_at_revision_0011_fixture_pins_schema_and_restores_head(
    db_at_revision_0011: None, engine: sa.Engine
) -> None:
    assert _current_revision(engine) == "0011_backfill_protected_persons"


def test_head_is_restored_after_db_at_revision_0011_fixture_teardown(engine: sa.Engine) -> None:
    """Runs independently of the test above: proves teardown already put the
    schema back at HEAD, not merely that the fixture *tries* to."""
    assert _current_revision(engine) == _HEAD_REVISION


class _SimulatedTestFailure(Exception):
    pass


def test_pinned_revision_context_restores_head_even_after_exception(engine: sa.Engine) -> None:
    assert _current_revision(engine) == _HEAD_REVISION

    with pytest.raises(_SimulatedTestFailure):
        with _db_pinned_to_revision(engine, "0011_backfill_protected_persons"):
            assert _current_revision(engine) == "0011_backfill_protected_persons"
            raise _SimulatedTestFailure("simulated failure inside historical-revision context")

    assert _current_revision(engine) == _HEAD_REVISION


def test_pinned_revision_context_rejects_starting_from_non_head(
    engine: sa.Engine, test_database_url: str
) -> None:
    """Guards against a prior test leaving the schema revision mutated: the
    context must refuse to start rather than silently downgrading from an
    already-wrong revision."""
    from alembic import command
    from alembic.config import Config

    from tests.conftest import _ALEMBIC_INI

    cfg = Config(str(_ALEMBIC_INI))
    command.downgrade(cfg, "0011_backfill_protected_persons")
    try:
        with pytest.raises(AssertionError, match="expects the suite to start at HEAD"):
            with _db_pinned_to_revision(engine, "0010_add_protected_persons"):
                pass  # pragma: no cover - assertion above fires before yield
    finally:
        command.upgrade(cfg, "head")

    assert _current_revision(engine) == _HEAD_REVISION
