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
from app.models.phase4d import (  # noqa: F401
    AiAssistSession,
    CacheConsumerCursor,
    CacheMetric,
    CustomerSnapshotCache,
    ForecastSnapshot,
    GenerationReading,
    SiteGeolocation,
    SysCacheOutbox,
    WeatherAdvisory,
)
from app.models.phase4e import (  # noqa: F401
    MfaFactor,
    MfaRecoveryCode,
    MfaTicket,
    StrongAuthGrant,
    TechnicianSyncOperation,
    WarrantyExtension,
    WarrantyExtensionOffer,
    WarrantyExtensionTerms,
    WebauthnChallenge,
    WebauthnCredential,
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

from app.models.coverage import OrderWarrantyTerm, ProductWarrantyPolicy, SerialWarranty  # noqa: F401
from app.models.custody import StockSerialMovement  # noqa: F401
from app.models.operations import GoodsReturn, StockAllocation, SupplierOrder  # noqa: F401
from app.models.provider import ProviderEvent, ProviderPaymentOrder  # noqa: F401
from app.models.rate_limit import RateLimitBucket  # noqa: F401
from app.models.scheduling import TechnicianAppointment, TechnicianAvailability, TechnicianLeave  # noqa: F401
from app.models.finance import (  # noqa: F401, E402
    FinanceEntry,
    FinanceEvidence,
    FinanceLine,
    FinancePeriod,
    FinanceRecord,
)
