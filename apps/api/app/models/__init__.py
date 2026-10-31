"""Import every model so Alembic and SQLAlchemy see one metadata registry."""

from app.models.audit import AuditEvent, SolarPackage
from app.models.enquiry import CustomerSite, Enquiry, EnquiryCounter, EnquiryStatusHistory
from app.models.identity import (
    CustomerProfile,
    EmailVerificationChallenge,
    EmployeeProfile,
    Role,
    Session,
    User,
)
from app.models.workflow import (  # noqa: F401
    CatalogueComponent,
    DocumentCounter,
    InstallationSchedulingRequest,
    PackageTemplateLine,
    PackageTemplateVersion,
    PaymentAttempt,
    PaymentIntent,
    PaymentRequirement,
    Quotation,
    QuotationAcceptance,
    QuotationLine,
    QuotationRevisionRequest,
    SalesOrder,
    SalesOrderLine,
    Survey,
    SurveyEvidence,
    SurveyStatusHistory,
    WarehousePreparationLine,
    WarehousePreparationRequest,
)

__all__ = [
    "AuditEvent",
    "CustomerProfile",
    "CustomerSite",
    "EmailVerificationChallenge",
    "EmployeeProfile",
    "Enquiry",
    "EnquiryCounter",
    "EnquiryStatusHistory",
    "Role",
    "Session",
    "SolarPackage",
    "User",
]
