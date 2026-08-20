"""Infraestructura de tests: guard de DB, engine/session aislados y cleanup.

Los repositories reales hacen session.commit() (ver app/repositories/*), por lo
que un simple BEGIN/ROLLBACK por test no aísla nada: los datos ya quedaron
persistidos. La estrategia aquí es DB de test dedicada + TRUNCATE ... CASCADE
después de cada test, con un guard que se re-valida inmediatamente antes de
cualquier operación destructiva.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401 - registra todas las tablas en Base.metadata
from app.core.db import Base, get_session
from app.core.security import hash_password
from app.core.settings import get_settings
from app.models import User
from app.repositories.users import create_user, mark_user_email_verified
from app.services.auth_sessions import create_auth_session

# Nombres de DB que jamás deben recibir TRUNCATE/DROP, incluso si alguien
# los nombrara terminando en "_test" por error de configuración.
_FORBIDDEN_DB_NAMES = {"protegid", "postgres", "template0", "template1"}
_FORBIDDEN_HOST_HINTS = ("prod", "staging")


class NotATestDatabaseError(RuntimeError):
    """La URL efectiva de DB no parece apuntar a una base de datos de test."""


def _effective_database_url() -> str:
    database_url = get_settings().database_url
    if not database_url:
        raise NotATestDatabaseError("DATABASE_URL no está configurada para esta corrida de tests.")

    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    return database_url


def assert_safe_test_database(url: str) -> None:
    """Guard obligatorio: aborta si la URL no corresponde inequívocamente a una DB de test.

    Se debe invocar inmediatamente antes de cualquier TRUNCATE/DROP/cleanup,
    no solo una vez al inicio de la sesión de pytest.
    """
    parsed = make_url(url)
    db_name = parsed.database or ""
    host = (parsed.host or "").lower()

    if not db_name.endswith("_test"):
        raise NotATestDatabaseError(
            f"Abortando: la base de datos {db_name!r} no termina en '_test'. "
            "Rehúso operar sobre algo que podría ser development/staging/production."
        )

    if db_name in _FORBIDDEN_DB_NAMES:
        raise NotATestDatabaseError(
            f"Abortando: {db_name!r} está en la lista explícita de bases de datos no-test."
        )

    if any(hint in host for hint in _FORBIDDEN_HOST_HINTS):
        raise NotATestDatabaseError(
            f"Abortando: el host {host!r} parece un entorno no-test."
        )


def _truncate_all_tables(engine: Engine, url: str) -> None:
    assert_safe_test_database(url)  # re-chequeo inmediatamente antes de la operación destructiva

    table_names = [table.name for table in Base.metadata.sorted_tables]
    if not table_names:
        return

    quoted = ", ".join(f'"{name}"' for name in table_names)
    with engine.begin() as connection:
        # Sin RESTART IDENTITY: las PK son UUID, no hay secuencias que reiniciar.
        # alembic_version no forma parte de Base.metadata, así que nunca se trunca.
        connection.execute(text(f"TRUNCATE TABLE {quoted} CASCADE"))


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = _effective_database_url()
    assert_safe_test_database(url)
    return url


@pytest.fixture(scope="session")
def engine(test_database_url: str) -> Generator[Engine, None, None]:
    assert_safe_test_database(test_database_url)
    eng = create_engine(test_database_url, pool_pre_ping=True)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _clean_database_after_test(
    engine: Engine, test_database_url: str
) -> Generator[None, None, None]:
    """Limpieza garantizada tras cada test, incluso si el test falla."""
    try:
        yield
    finally:
        _truncate_all_tables(engine, test_database_url)


@pytest.fixture(autouse=True)
def _flush_rate_limit_state_before_test() -> Generator[None, None, None]:
    """Los endpoints con check_rate_limit comparten Redis con clave por
    IP/public_id/email. Sin flush, tests de activación/perfil público que
    corren en la misma suite compartirían contadores y se bloquearían entre
    sí con 429 espurios. Best-effort: si REDIS_URL no está configurada
    (suites que no tocan endpoints con rate limit), no hace nada."""
    if get_settings().redis_url:
        from app.core.redis import get_redis_client

        get_redis_client().flushdb()
    yield


@pytest.fixture
def db_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(session_factory: sessionmaker[Session], test_database_url: str) -> Generator[TestClient, None, None]:
    """TestClient con la dependency de DB real sobreescrita hacia la DB de test."""
    assert_safe_test_database(test_database_url)

    def _override_get_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    from app.main import app  # import diferido: evita tocar la app antes de validar el guard

    app.dependency_overrides[get_session] = _override_get_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)


class AuthedUser:
    """Credenciales HTTP de un usuario autenticado para tests: cookies para
    cualquier request, headers adicionales requeridos solo en las
    state-changing (POST/PUT/PATCH/DELETE) por el middleware CSRF."""

    def __init__(self, user: User, cookies: dict[str, str], headers: dict[str, str]) -> None:
        self.user = user
        self.cookies = cookies
        self.headers = headers


@pytest.fixture
def make_authed_user(session_factory: sessionmaker[Session]):
    """Crea un usuario (verificado por default) con una AuthSession real y
    las cookies/headers necesarios para autenticarse contra `client`, sin
    pasar por el endpoint HTTP de login (evita acoplar cada test a
    rate-limits/flows de auth que no son el objeto de este bloque)."""

    from uuid import uuid4

    def _make(*, email: str | None = None, verified: bool = True) -> AuthedUser:
        session = session_factory()
        try:
            user = create_user(
                session,
                email=email or f"{uuid4().hex}@example.com",
                password_hash=hash_password("Sup3rSecret!1"),
            )
            if verified:
                mark_user_email_verified(session, user)

            _, session_token = create_auth_session(session, user.id)
        finally:
            session.close()

        settings = get_settings()
        csrf_token = f"csrf-{uuid4().hex}"
        cookies = {
            settings.session_cookie_name: session_token,
            settings.csrf_cookie_name: csrf_token,
        }
        headers = {settings.csrf_header_name: csrf_token}
        return AuthedUser(user=user, cookies=cookies, headers=headers)

    return _make
