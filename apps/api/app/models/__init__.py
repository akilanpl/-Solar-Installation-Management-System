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
from app.models.phase3 import (  # noqa: F401
    Delivery,
    DeliveryLine,
    EquipmentSerial,
    InstallationEvidence,
    InstallationJob,
    InstallationOtp,
    ReplenishmentRequest,
    StockLedger,
    StockOperation,
    StockOperationLine,
    StockReservation,
    WarehouseLocation,
    Warranty,
)
from app.models.support import (  # noqa: F401
    ResolutionAcknowledgment,
    ServiceTicket,
    ServiceTicketAttachment,
    ServiceTicketEvent,
    TicketRepairJob,
)
from app.models.warranty import (  # noqa: F401
    CoverageDecision,
    EstimateDecision,
    ReplacementDecision,
    ReturnInspection,
    SerializedAssetCoverage,
    ServiceCreditNote,
    ServiceEstimate,
    ServiceInvoice,
    ServicePriceBook,
    ServiceTaxPolicy,
    WarrantyException,
    WarrantyPolicy,
    WarrantyPolicyVersion,
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
