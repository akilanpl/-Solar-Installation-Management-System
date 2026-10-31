"""Database queries. Business rules live in services, not here."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.audit import AuditEvent, SolarPackage
from app.models.enquiry import Enquiry
from app.models.identity import (
    EmailVerificationChallenge,
    EmployeeProfile,
    Role,
    User,
)
from app.models.identity import (
    Session as DbSession,
)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_user_by_employee_code(db: Session, employee_code: str) -> User | None:
    profile = db.scalar(
        select(EmployeeProfile).where(EmployeeProfile.employee_code == employee_code)
    )
    if profile is None:
        return None
    return db.get(User, profile.user_id)


def get_role(db: Session, code: str) -> Role | None:
    return db.get(Role, code)


def active_challenge(db: Session, user_id: uuid.UUID) -> EmailVerificationChallenge | None:
    return db.scalar(
        select(EmailVerificationChallenge)
        .where(
            EmailVerificationChallenge.user_id == user_id,
            EmailVerificationChallenge.purpose == "signup_verify",
            EmailVerificationChallenge.consumed_at.is_(None),
        )
        .order_by(EmailVerificationChallenge.created_at.desc())
    )


def get_session_by_hash(db: Session, token_hash: str) -> DbSession | None:
    return db.scalar(select(DbSession).where(DbSession.token_hash == token_hash))


def enquiry_by_idempotency(
    db: Session, customer_user_id: uuid.UUID, idempotency_key: str
) -> Enquiry | None:
    return db.scalar(
        select(Enquiry).where(
            Enquiry.customer_user_id == customer_user_id,
            Enquiry.idempotency_key == idempotency_key,
        )
    )


def get_enquiry(db: Session, enquiry_id: uuid.UUID) -> Enquiry | None:
    from app.models.enquiry import EnquiryStatusHistory

    return db.scalar(
        select(Enquiry)
        .execution_options(populate_existing=True)
        .options(
            selectinload(Enquiry.site),
            selectinload(Enquiry.history).selectinload(EnquiryStatusHistory.actor),
        )
        .where(Enquiry.id == enquiry_id)
    )


def list_packages(db: Session) -> list[SolarPackage]:
    return list(db.scalars(select(SolarPackage).order_by(SolarPackage.code)))


def list_employees(db: Session) -> list[tuple[User, EmployeeProfile]]:
    rows = db.execute(
        select(User, EmployeeProfile)
        .join(EmployeeProfile, EmployeeProfile.user_id == User.id)
        .order_by(EmployeeProfile.employee_code)
    ).all()
    return [(user, profile) for user, profile in rows]


def add_audit(
    db: Session,
    *,
    actor_user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    metadata: dict,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata,
    )
    db.add(event)
    return event
