"""Synchronous SQLAlchemy sessions.

SolarOps uses synchronous sessions on purpose. Alembic, Pytest, and the
request-scoped transaction below are all synchronous, so one execution model
covers migrations, tests, and HTTP handlers. Async sessions would not remove
a real bottleneck at the current scale (about 40 installations a month) and
would force a second database driver pattern.

Each HTTP request gets one session. Every consumer uses function scope, so the
dependency commits before success headers/cookies leave the app, and rolls back
if the handler or commit fails. Services flush inside that transaction.
The one exception is a failed OTP attempt, which must persist and is documented
in the auth service.
"""

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def build_engine(database_url: str):
    engine = create_engine(database_url, pool_pre_ping=True)

    @event.listens_for(engine, "connect")
    def _set_utc(dbapi_connection, _connection_record) -> None:
        # SET is transactional in PostgreSQL. Persist the session setting
        # outside a transaction so pool rollback cannot restore the server's
        # local timezone after the first checkout.
        previous_autocommit = dbapi_connection.autocommit
        try:
            dbapi_connection.autocommit = True
            with dbapi_connection.cursor() as cursor:
                cursor.execute("SET TIME ZONE 'UTC'")
        finally:
            dbapi_connection.autocommit = previous_autocommit

    return engine


def build_session_factory(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db(request: Request) -> Generator[Session, None, None]:
    session = request.app.state.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
