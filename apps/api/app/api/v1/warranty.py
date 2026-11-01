"""Phase 4B warranty intelligence: policies, serial coverage, decisions."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.identity import User
from app.models.phase3 import EquipmentSerial
from app.models.warranty import (
    CoverageDecision,
    SerializedAssetCoverage,
    WarrantyPolicyVersion,
)
from app.schemas import parse_idempotency_key
from app.schemas.warranty import (
    CoverageResponse,
    DecisionCreate,
    DecisionResponse,
    ExceptionCreate,
    ExceptionResponse,
    PolicyCreate,
    PolicyResponse,
    PolicyVersionCreate,
    PolicyVersionResponse,
    VoidCreate,
)
from app.services import warranty_service

router = APIRouter(tags=["warranty"])


def _key(value: str | None) -> str:
    try:
        return parse_idempotency_key(value)
    except ValueError as exc:
        raise AppError(400, "idempotency_key_required", str(exc)) from exc


def _version_response(version: WarrantyPolicyVersion) -> PolicyVersionResponse:
    return PolicyVersionResponse(
        id=version.id, policy_id=version.policy_id, version_number=version.version_number,
        duration_days=version.duration_days,
        applicable_components=version.applicable_components,
        covered_fault_categories=version.covered_fault_categories,
        covered_components=version.covered_components,
        covered_repair_types=version.covered_repair_types,
        exclusions=version.exclusions, labour_covered=version.labour_covered,
        replacement_allowed=version.replacement_allowed,
        replacement_continuation=version.replacement_continuation,
        replacement_warranty_days=version.replacement_warranty_days,
        manufacturer_auth_required=version.manufacturer_auth_required,
        repeat_replacement_allowed=version.repeat_replacement_allowed,
        effective_from=version.effective_from, effective_to=version.effective_to,
        created_at=version.created_at,
    )


def _coverage_response(db: Session, coverage: SerializedAssetCoverage) -> CoverageResponse:
    serial = db.get(EquipmentSerial, coverage.serial_id)
    version = db.get(WarrantyPolicyVersion, coverage.policy_version_id)
    policy_code = None
    if version is not None:
        from app.models.warranty import WarrantyPolicy

        policy = db.get(WarrantyPolicy, version.policy_id)
        policy_code = policy.code if policy else None
    return CoverageResponse(
        coverage_id=coverage.id,
        serial_number=serial.serial_number if serial else None,
        component_code=serial.component_code if serial else None,
        policy_code=policy_code,
        policy_version=version.version_number if version else None,
        status=coverage.status, starts_at=coverage.starts_at, ends_at=coverage.ends_at,
        order_id=coverage.order_id,
    )


def _decision_response(db: Session, decision: CoverageDecision) -> DecisionResponse:
    serial = db.get(EquipmentSerial, decision.serial_id)
    version = (
        db.get(WarrantyPolicyVersion, decision.policy_version_id)
        if decision.policy_version_id else None
    )
    coverage = (
        db.get(SerializedAssetCoverage, decision.coverage_id)
        if decision.coverage_id else None
    )
    return DecisionResponse(
        id=decision.id, ticket_id=decision.ticket_id,
        serial_number=serial.serial_number if serial else "",
        policy_version=version.version_number if version else None,
        fault_category=decision.fault_category, evaluated_at=decision.evaluated_at,
        verdict=decision.verdict, reason=decision.reason,
        coverage_status=coverage.status if coverage else None,
        created_at=decision.created_at,
    )


@router.post("/warranty/policies", response_model=PolicyResponse, status_code=201)
def create_policy(payload: PolicyCreate, user: User = Depends(current_user),
                  db: Session = Depends(get_db, scope="function")):
    policy = warranty_service.create_policy(
        db, user, payload.code, payload.issuer, payload.category, payload.description)
    return PolicyResponse(
        id=policy.id, code=policy.code, issuer=policy.issuer, category=policy.category,
        description=policy.description, created_at=policy.created_at)


@router.get("/warranty/policies", response_model=list[PolicyResponse])
def list_policies(user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return [
        PolicyResponse(
            id=policy.id, code=policy.code, issuer=policy.issuer, category=policy.category,
            description=policy.description, created_at=policy.created_at)
        for policy in warranty_service.list_policies(db, user)
    ]


@router.post("/warranty/policies/{policy_id}/versions", response_model=PolicyVersionResponse,
             status_code=201)
def create_policy_version(policy_id: UUID, payload: PolicyVersionCreate,
                           user: User = Depends(current_user),
                           db: Session = Depends(get_db, scope="function")):
    return _version_response(warranty_service.create_policy_version(
        db, user, policy_id, payload.model_dump()))


@router.get("/warranty/policies/{policy_id}/versions",
            response_model=list[PolicyVersionResponse])
def list_policy_versions(policy_id: UUID, user: User = Depends(current_user),
                         db: Session = Depends(get_db, scope="function")):
    return [_version_response(version)
            for version in warranty_service.list_policy_versions(db, user, policy_id)]


@router.post("/warranty/orders/{order_id}/activate-coverages",
             response_model=list[CoverageResponse], status_code=201)
def activate_coverages(order_id: UUID, user: User = Depends(current_user),
                       db: Session = Depends(get_db, scope="function")):
    return [_coverage_response(db, coverage) for coverage in
            warranty_service.activate_coverages_for_order(db, user, order_id)]


@router.post("/warranty/coverage-decisions", response_model=DecisionResponse, status_code=201)
def decide_coverage(payload: DecisionCreate, response: Response,
                    user: User = Depends(current_user), db: Session = Depends(get_db, scope="function"),
                    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    decision, created = warranty_service.evaluate_coverage(
        db, user, payload.ticket_id, payload.serial_number, payload.fault_category,
        payload.evaluated_at, _key(idempotency_key))
    if not created:
        response.status_code = 200
    return _decision_response(db, decision)


@router.get("/warranty/coverage-decisions", response_model=list[DecisionResponse])
def list_ticket_decisions(ticket_id: UUID = Query(...), user: User = Depends(current_user),
                          db: Session = Depends(get_db, scope="function")):
    return [_decision_response(db, decision) for decision in
            warranty_service.ticket_decisions(db, user, ticket_id)]


@router.get("/warranty/serials/mine", response_model=list[CoverageResponse])
def my_coverages(user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    result = []
    for entry in warranty_service.my_coverages(db, user):
        coverage = db.get(SerializedAssetCoverage, entry["coverage_id"])
        assert coverage is not None
        result.append(_coverage_response(db, coverage))
    return result


@router.get("/warranty/serials/lookup")
def lookup_serial(serial_number: str = Query(min_length=1, max_length=64),
                  user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    found = warranty_service.lookup_serial(db, user, serial_number)
    coverage = found.pop("coverage")
    if coverage is not None:
        row = db.get(SerializedAssetCoverage, coverage["coverage_id"])
        assert row is not None
        coverage = _coverage_response(db, row).model_dump(mode="json")
    found["coverage"] = coverage
    return found


@router.post("/warranty/exceptions", response_model=ExceptionResponse, status_code=201)
def create_exception(payload: ExceptionCreate, user: User = Depends(current_user),
                     db: Session = Depends(get_db, scope="function")):
    row = warranty_service.create_exception(
        db, user, payload.ticket_id, payload.serial_number, payload.decision,
        payload.reason, payload.evidence_ref)
    return ExceptionResponse(
        id=row.id, ticket_id=row.ticket_id, decision=row.decision, reason=row.reason,
        evidence_ref=row.evidence_ref, created_at=row.created_at)


@router.post("/warranty/coverages/{coverage_id}/void", response_model=CoverageResponse)
def void_coverage(coverage_id: UUID, payload: VoidCreate,
                  user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return _coverage_response(
        db, warranty_service.void_coverage(db, user, coverage_id, payload.reason))
