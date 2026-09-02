"""Fase 4E: generate_unique_public_id debe considerar también Devices soft-deleted,
ya que UNIQUE(public_id) en PostgreSQL no excluye deleted_at."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import sessionmaker

from app.services.devices import create_pending_device, generate_unique_public_id
from tests.helpers import create_pending_device_with_claim_code


def _soft_delete(session, device) -> None:
    device.deleted_at = datetime.now(UTC)
    session.commit()
    session.refresh(device)


def test_generate_unique_public_id_skips_soft_deleted_public_id(
    session_factory: sessionmaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = session_factory()
    try:
        deleted_device, _claim_code = create_pending_device_with_claim_code(session)
        occupied_public_id = deleted_device.public_id
        _soft_delete(session, deleted_device)

        candidates = iter([occupied_public_id, "PID-FREEFREEFR"])
        monkeypatch.setattr(
            "app.services.devices.generate_public_id", lambda: next(candidates)
        )

        result = generate_unique_public_id(session)

        assert result == "PID-FREEFREEFR"
    finally:
        session.close()


def test_create_pending_device_skips_soft_deleted_public_id(
    session_factory: sessionmaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = session_factory()
    try:
        deleted_device, _claim_code = create_pending_device_with_claim_code(session)
        occupied_public_id = deleted_device.public_id
        _soft_delete(session, deleted_device)

        candidates = iter([occupied_public_id, "PID-FREEFREEFR"])
        monkeypatch.setattr(
            "app.services.devices.generate_public_id", lambda: next(candidates)
        )

        new_device = create_pending_device(session)

        assert new_device.public_id == "PID-FREEFREEFR"
    finally:
        session.close()
