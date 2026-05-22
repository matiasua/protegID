"""Generación de identificadores públicos de dispositivos."""

from secrets import choice


PUBLIC_ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PUBLIC_ID_PREFIX = "PID"
PUBLIC_ID_RANDOM_LENGTH = 10


def generate_public_id() -> str:
    random_part = "".join(
        choice(PUBLIC_ID_ALPHABET) for _ in range(PUBLIC_ID_RANDOM_LENGTH)
    )
    return f"{PUBLIC_ID_PREFIX}-{random_part}"
