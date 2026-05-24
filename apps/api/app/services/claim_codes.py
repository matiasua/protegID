"""Generación y validación segura de códigos privados de claim."""

from secrets import choice

from app.core.security import hash_password, verify_password


CLAIM_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CLAIM_CODE_GROUP_LENGTH = 4
CLAIM_CODE_GROUPS = 3
CLAIM_CODE_LENGTH = CLAIM_CODE_GROUP_LENGTH * CLAIM_CODE_GROUPS


def generate_claim_code() -> str:
    raw_code = "".join(choice(CLAIM_CODE_ALPHABET) for _ in range(CLAIM_CODE_LENGTH))
    return _format_claim_code(raw_code)


def normalize_claim_code(claim_code: str) -> str:
    raw_code = claim_code.strip().upper().replace("-", "").replace(" ", "")
    return _format_claim_code(raw_code)


def hash_claim_code(claim_code: str) -> str:
    normalized_claim_code = normalize_claim_code(claim_code)
    return hash_password(normalized_claim_code)


def verify_claim_code(claim_code: str, claim_code_hash: str | None) -> bool:
    if not claim_code.strip() or not claim_code_hash:
        return False

    normalized_claim_code = normalize_claim_code(claim_code)
    if len(normalized_claim_code.replace("-", "")) != CLAIM_CODE_LENGTH:
        return False

    return verify_password(normalized_claim_code, claim_code_hash)


def _format_claim_code(raw_code: str) -> str:
    return "-".join(
        raw_code[index : index + CLAIM_CODE_GROUP_LENGTH]
        for index in range(0, len(raw_code), CLAIM_CODE_GROUP_LENGTH)
    )
