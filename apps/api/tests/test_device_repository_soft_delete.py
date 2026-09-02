"""Fase 4A: lookups normales excluyen soft-deleted; variantes including_deleted no."""

from datetime import UTC, datetime

from sqlalchemy.orm import sessionmaker

from app.repositories.devices import (
    get_device_by_id,
    get_device_by_id_including_deleted,
    get_device_by_public_id,
    get_device_by_public_id_including_deleted,
    get_devices_by_user_id,
    get_devices_by_user_id_including_deleted,
)
from tests.helpers import create_pending_device_with_claim_code, make_active_device_for_protected_person


def _soft_delete(session, device) -> None:
    device.deleted_at = datetime.now(UTC)
    session.commit()
    session.refresh(device)


def test_get_device_by_id_excludes_soft_deleted(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        device, _claim_code = create_pending_device_with_claim_code(session)
        _soft_delete(session, device)

        assert get_device_by_id(session, device.id) is None
    finally:
        session.close()


def test_get_device_by_public_id_excludes_soft_deleted(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        device, _claim_code = create_pending_device_with_claim_code(session)
        _soft_delete(session, device)

        assert get_device_by_public_id(session, device.public_id) is None
    finally:
        session.close()


def test_get_devices_by_user_id_excludes_soft_deleted(
    session_factory: sessionmaker, make_authed_user
) -> None:
    session = session_factory()
    try:
        authed = make_authed_user()
        device = make_active_device_for_protected_person(
            session, user_id=authed.user.id, protected_person_id=None
        )
        _soft_delete(session, device)

        assert get_devices_by_user_id(session, authed.user.id) == []
    finally:
        session.close()


def test_get_device_by_id_including_deleted_finds_soft_deleted(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        device, _claim_code = create_pending_device_with_claim_code(session)
        _soft_delete(session, device)

        found = get_device_by_id_including_deleted(session, device.id)
        assert found is not None
        assert found.id == device.id
    finally:
        session.close()


def test_get_device_by_public_id_including_deleted_finds_soft_deleted(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        device, _claim_code = create_pending_device_with_claim_code(session)
        _soft_delete(session, device)

        found = get_device_by_public_id_including_deleted(session, device.public_id)
        assert found is not None
        assert found.id == device.id
    finally:
        session.close()


def test_get_devices_by_user_id_including_deleted_finds_soft_deleted(
    session_factory: sessionmaker, make_authed_user
) -> None:
    session = session_factory()
    try:
        authed = make_authed_user()
        device = make_active_device_for_protected_person(
            session, user_id=authed.user.id, protected_person_id=None
        )
        _soft_delete(session, device)

        found = get_devices_by_user_id_including_deleted(session, authed.user.id)
        assert [d.id for d in found] == [device.id]
    finally:
        session.close()
