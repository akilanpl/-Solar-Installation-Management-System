"""Map enquiry rows to response models while the session is open."""

from app.models.enquiry import Enquiry
from app.schemas import EnquiryDetail, EnquirySummary, HistoryResponse, SiteResponse


def summary_from(enquiry: Enquiry) -> EnquirySummary:
    return EnquirySummary(
        id=enquiry.id,
        reference=enquiry.reference,
        status=enquiry.status,  # type: ignore[arg-type]
        contact_name=enquiry.contact_name,
        preferred_capacity_w=enquiry.preferred_capacity_w,
        grid_preference=enquiry.grid_preference,  # type: ignore[arg-type]
        monthly_bill_minor=enquiry.monthly_bill_minor,
        currency_code=enquiry.currency_code,
        subsidy_interest=enquiry.subsidy_interest,
        shadow_free_area_sqm=enquiry.shadow_free_area_sqm,
        grid_connection_suitable=enquiry.grid_connection_suitable,
        decision_by_user_id=enquiry.decision_by_user_id,
        decision_at=enquiry.decision_at,
        qualification_note=enquiry.qualification_note,
        created_at=enquiry.created_at,
        updated_at=enquiry.updated_at,
    )


def detail_from(enquiry: Enquiry) -> EnquiryDetail:
    site = enquiry.site
    history = [
        HistoryResponse(
            id=item.id,
            from_status=item.from_status,
            to_status=item.to_status,
            actor_role=item.actor.role_code,
            note=item.note,
            created_at=item.created_at,
        )
        for item in enquiry.history
    ]
    base = summary_from(enquiry)
    return EnquiryDetail(
        **base.model_dump(),
        contact_phone=enquiry.contact_phone,
        contact_email=enquiry.contact_email,
        site=SiteResponse(
            id=site.id,
            line1=site.line1,
            line2=site.line2,
            city=site.city,
            state=site.state,
            postal_code=site.postal_code,
            country_code=site.country_code,
        ),
        history=history,
    )
