"""Bloque 2: nuevo motor de estados (ProfileReadiness, PublicationEligibility,
PublicAccessStatus), en paralelo al legacy `profile_readiness.py`.

Funciones puras, sin DB: los modelos se construyen en memoria (nunca
persistidos) para representar fielmente los objetos de dominio reales, sin
necesitar la infraestructura de test de DB para esto.
"""

from datetime import UTC, datetime

from app.core.settings import get_settings
from app.models import Device, EmergencyProfile, ProtectedPerson
from app.services.emergency_profile_status import (
    calculate_public_access_status,
    calculate_profile_readiness,
    calculate_publication_eligibility,
)

_VALID_CONSENT_VERSION = get_settings().public_profile_consent_version
_OUTDATED_CONSENT_VERSION = f"outdated-{_VALID_CONSENT_VERSION}"


def _profile(**overrides: object) -> EmergencyProfile:
    defaults: dict[str, object] = {
        "display_name": None,
        "emergency_contact_name": None,
        "emergency_contact_phone": None,
        "emergency_contact_relationship": None,
        "medical_conditions": None,
        "medical_conditions_none": False,
        "allergies": None,
        "allergies_none": False,
        "medications": None,
        "medications_none": False,
        "blood_type": None,
        "notes": None,
        "is_public": False,
        "deleted_at": None,
        "public_consent_accepted_at": None,
        "public_consent_version": None,
    }
    defaults.update(overrides)
    return EmergencyProfile(**defaults)


def _ready_profile(**overrides: object) -> EmergencyProfile:
    ready_defaults: dict[str, object] = {
        "display_name": "Ana",
        "emergency_contact_name": "Luis",
        "emergency_contact_phone": "+56911111111",
        "medical_conditions_none": True,
        "allergies_none": True,
    }
    ready_defaults.update(overrides)
    return _profile(**ready_defaults)


def _consented_profile(**overrides: object) -> EmergencyProfile:
    consented_defaults: dict[str, object] = {
        "is_public": True,
        "public_consent_accepted_at": datetime.now(UTC),
        "public_consent_version": _VALID_CONSENT_VERSION,
    }
    consented_defaults.update(overrides)
    return _ready_profile(**consented_defaults)


# ---------------------------------------------------------------------------
# ProfileReadiness
# ---------------------------------------------------------------------------


def test_readiness_profile_none_is_incomplete() -> None:
    readiness = calculate_profile_readiness(None)

    assert readiness.is_ready is False
    assert set(readiness.missing_fields) == set(readiness.required_fields)


def test_readiness_all_required_fields_present_is_ready() -> None:
    readiness = calculate_profile_readiness(_ready_profile())

    assert readiness.is_ready is True
    assert readiness.missing_fields == []


def test_readiness_missing_display_name_is_incomplete() -> None:
    readiness = calculate_profile_readiness(_ready_profile(display_name=None))

    assert readiness.is_ready is False
    assert "display_name" in readiness.missing_fields


def test_readiness_missing_emergency_contact_name_is_incomplete() -> None:
    readiness = calculate_profile_readiness(_ready_profile(emergency_contact_name=None))

    assert readiness.is_ready is False
    assert "emergency_contact_name" in readiness.missing_fields


def test_readiness_missing_emergency_contact_phone_is_incomplete() -> None:
    readiness = calculate_profile_readiness(_ready_profile(emergency_contact_phone=None))

    assert readiness.is_ready is False
    assert "emergency_contact_phone" in readiness.missing_fields


def test_readiness_medical_conditions_with_text_is_complete() -> None:
    readiness = calculate_profile_readiness(
        _ready_profile(medical_conditions_none=False, medical_conditions="Asma")
    )

    assert "medical_conditions_decision" in readiness.completed_fields


def test_readiness_medical_conditions_none_true_is_complete() -> None:
    readiness = calculate_profile_readiness(
        _ready_profile(medical_conditions_none=True, medical_conditions=None)
    )

    assert "medical_conditions_decision" in readiness.completed_fields


def test_readiness_medical_conditions_without_text_or_none_is_missing() -> None:
    readiness = calculate_profile_readiness(
        _ready_profile(medical_conditions_none=False, medical_conditions=None)
    )

    assert "medical_conditions_decision" in readiness.missing_fields
    assert readiness.is_ready is False


def test_readiness_allergies_with_text_is_complete() -> None:
    readiness = calculate_profile_readiness(
        _ready_profile(allergies_none=False, allergies="Polen")
    )

    assert "allergies_decision" in readiness.completed_fields


def test_readiness_allergies_none_true_is_complete() -> None:
    readiness = calculate_profile_readiness(
        _ready_profile(allergies_none=True, allergies=None)
    )

    assert "allergies_decision" in readiness.completed_fields


def test_readiness_allergies_without_decision_is_missing() -> None:
    readiness = calculate_profile_readiness(
        _ready_profile(allergies_none=False, allergies=None)
    )

    assert "allergies_decision" in readiness.missing_fields
    assert readiness.is_ready is False


def test_readiness_empty_emergency_contact_relationship_does_not_block() -> None:
    readiness = calculate_profile_readiness(
        _ready_profile(emergency_contact_relationship=None)
    )

    assert readiness.is_ready is True


def test_readiness_empty_medications_does_not_block() -> None:
    readiness = calculate_profile_readiness(
        _ready_profile(medications=None, medications_none=False)
    )

    assert readiness.is_ready is True


def test_readiness_empty_blood_type_does_not_block() -> None:
    readiness = calculate_profile_readiness(_ready_profile(blood_type=None))

    assert readiness.is_ready is True


def test_readiness_empty_notes_does_not_block() -> None:
    readiness = calculate_profile_readiness(_ready_profile(notes=None))

    assert readiness.is_ready is True


def test_readiness_device_lost_does_not_convert_ready_into_incomplete() -> None:
    """ProfileReadiness ni siquiera acepta un Device: garantia estructural."""
    import inspect

    params = inspect.signature(calculate_profile_readiness).parameters
    assert set(params) == {"profile"}

    # Y aunque el Device de un dispositivo puntual este LOST, el profile
    # sigue siendo el mismo objeto: su readiness no puede cambiar por eso.
    readiness = calculate_profile_readiness(_ready_profile())
    assert readiness.is_ready is True


# ---------------------------------------------------------------------------
# PublicationEligibility
# ---------------------------------------------------------------------------


def test_eligibility_ready_and_valid_consent_can_publish() -> None:
    eligibility = calculate_publication_eligibility(_consented_profile())

    assert eligibility.can_publish is True


def test_eligibility_incomplete_profile_with_valid_consent_cannot_publish() -> None:
    profile = _consented_profile(display_name=None)

    eligibility = calculate_publication_eligibility(profile)

    assert eligibility.profile_ready is False
    assert eligibility.can_publish is False


def test_eligibility_ready_without_consent_cannot_publish() -> None:
    profile = _ready_profile(public_consent_accepted_at=None, public_consent_version=None)

    eligibility = calculate_publication_eligibility(profile)

    assert eligibility.profile_ready is True
    assert eligibility.consent_valid is False
    assert eligibility.can_publish is False


def test_eligibility_ready_with_outdated_consent_version_cannot_publish() -> None:
    profile = _consented_profile(public_consent_version=_OUTDATED_CONSENT_VERSION)

    eligibility = calculate_publication_eligibility(profile)

    assert eligibility.profile_ready is True
    assert eligibility.consent_valid is False
    assert eligibility.can_publish is False


def test_eligibility_is_independent_of_visibility() -> None:
    """profile.is_public == False no implica can_publish == False.

    ELIGIBILITY (puede publicarse) y VISIBILITY (esta publicado) son estados
    separados por diseno.
    """
    profile = _consented_profile(is_public=False)

    eligibility = calculate_publication_eligibility(profile)

    assert eligibility.can_publish is True


# ---------------------------------------------------------------------------
# PublicAccessStatus
# ---------------------------------------------------------------------------


def _active_device(**overrides: object) -> Device:
    defaults: dict[str, object] = {"status": "active", "deleted_at": None}
    defaults.update(overrides)
    return Device(**defaults)


def _active_person(**overrides: object) -> ProtectedPerson:
    defaults: dict[str, object] = {"deleted_at": None}
    defaults.update(overrides)
    return ProtectedPerson(**defaults)


def test_access_status_fully_operational() -> None:
    access = calculate_public_access_status(
        _active_device(), _active_person(), _consented_profile()
    )

    assert access.is_operational is True
    assert access.blocking_reasons == []


def test_access_status_device_lost_is_not_operational() -> None:
    access = calculate_public_access_status(
        _active_device(status="lost"), _active_person(), _consented_profile()
    )

    assert access.is_operational is False
    assert "device_not_active" in access.blocking_reasons


def test_access_status_device_disabled_is_not_operational() -> None:
    access = calculate_public_access_status(
        _active_device(status="disabled"), _active_person(), _consented_profile()
    )

    assert access.is_operational is False
    assert "device_not_active" in access.blocking_reasons


def test_access_status_device_pending_activation_is_not_operational() -> None:
    access = calculate_public_access_status(
        _active_device(status="pending_activation"),
        _active_person(),
        _consented_profile(),
    )

    assert access.is_operational is False
    assert "device_not_active" in access.blocking_reasons


def test_access_status_device_soft_deleted_is_not_operational() -> None:
    access = calculate_public_access_status(
        _active_device(deleted_at=datetime.now(UTC)),
        _active_person(),
        _consented_profile(),
    )

    assert access.is_operational is False
    assert "device_deleted" in access.blocking_reasons


def test_access_status_protected_person_soft_deleted_is_not_operational() -> None:
    access = calculate_public_access_status(
        _active_device(),
        _active_person(deleted_at=datetime.now(UTC)),
        _consented_profile(),
    )

    assert access.is_operational is False
    assert "protected_person_deleted" in access.blocking_reasons


def test_access_status_profile_soft_deleted_is_not_operational() -> None:
    access = calculate_public_access_status(
        _active_device(),
        _active_person(),
        _consented_profile(deleted_at=datetime.now(UTC)),
    )

    assert access.is_operational is False
    assert "profile_deleted" in access.blocking_reasons


def test_access_status_profile_private_is_not_operational() -> None:
    access = calculate_public_access_status(
        _active_device(), _active_person(), _consented_profile(is_public=False)
    )

    assert access.is_operational is False
    assert "profile_private" in access.blocking_reasons


def test_access_status_invalid_consent_is_not_operational() -> None:
    access = calculate_public_access_status(
        _active_device(),
        _active_person(),
        _consented_profile(public_consent_accepted_at=None),
    )

    assert access.is_operational is False
    assert "publication_not_eligible" in access.blocking_reasons


def test_access_status_incomplete_profile_is_not_operational() -> None:
    access = calculate_public_access_status(
        _active_device(), _active_person(), _consented_profile(display_name=None)
    )

    assert access.is_operational is False
    assert "publication_not_eligible" in access.blocking_reasons


# ---------------------------------------------------------------------------
# Escenario critico: un profile READY es independiente del Device puntual que
# lo consulta. Dos devices distintos sobre el mismo profile pueden divergir
# en PublicAccessStatus sin que ProfileReadiness se vea afectado.
# ---------------------------------------------------------------------------


def test_readiness_is_shared_but_access_status_diverges_per_device() -> None:
    profile = _consented_profile()
    person = _active_person()

    device_a = _active_device()
    device_b = _active_device()

    readiness_before = calculate_profile_readiness(profile)
    assert readiness_before.is_ready is True

    # Device A se pierde. El profile en si no cambia.
    device_a.status = "lost"

    readiness_after = calculate_profile_readiness(profile)
    assert readiness_after.is_ready is True

    access_a = calculate_public_access_status(device_a, person, profile)
    access_b = calculate_public_access_status(device_b, person, profile)

    assert access_a.is_operational is False
    assert "device_not_active" in access_a.blocking_reasons
    assert access_b.is_operational is True
