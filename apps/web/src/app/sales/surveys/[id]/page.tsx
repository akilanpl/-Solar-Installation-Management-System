"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Workspace } from "@/components/workspace";
import { Button, Card, ConfirmDialog, ErrorState, LoadingState, Notice, PageHeader, SelectField, StatusBadge, TextArea, TextField } from "@/components/ui";
import {
  api,
  ApiError,
  idempotencyKey,
  type EnquiryDetail,
  type PackageResponse,
  type QuotationResponse,
  type SurveyResponse,
  type TechnicianOption,
  type TemplateVersionResponse,
} from "@/lib/api";
import { formatInrFromPaise, formatWhen, rupeesToPaise, statusLabel } from "@/lib/format";

export default function SalesSurveyPage() {
  const params = useParams<{ id: string }>();
  return (
    <Workspace path={`/sales/surveys/${params.id}`}>
      {() => <SurveyReview id={params.id} />}
    </Workspace>
  );
}

function SurveyReview({ id }: { id: string }) {
  const router = useRouter();
  const [survey, setSurvey] = useState<SurveyResponse | null>(null);
  const [enquiry, setEnquiry] = useState<EnquiryDetail | null>(null);
  const [technicians, setTechnicians] = useState<TechnicianOption[]>([]);
  const [packages, setPackages] = useState<PackageResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [technicianId, setTechnicianId] = useState("");
  const [appointment, setAppointment] = useState("");
  const [note, setNote] = useState("");
  const [packageCode, setPackageCode] = useState("");
  const [discount, setDiscount] = useState("");
  const [preview, setPreview] = useState<TemplateVersionResponse | null>(null);
  const [confirm, setConfirm] = useState<null | "approve" | "reject" | "resurvey" | "quote">(null);

  function load() {
    setError(null);
    api<SurveyResponse>(`/api/v1/surveys/${id}`)
      .then((body) => {
        setSurvey(body);
        return Promise.all([
          api<EnquiryDetail>(`/api/v1/enquiries/${body.enquiry_id}`),
          api<TechnicianOption[]>("/api/v1/technicians"),
          api<PackageResponse[]>("/api/v1/packages"),
        ]);
      })
      .then(([enquiryBody, technicianBody, packageBody]) => {
        setEnquiry(enquiryBody);
        setTechnicians(technicianBody);
        const matching = packageBody.filter(
          (item) =>
            item.is_active &&
            item.category === "package" &&
            item.capacity_w === enquiryBody.preferred_capacity_w &&
            item.grid_type === enquiryBody.grid_preference,
        );
        setPackages(matching);
        if (matching[0]) setPackageCode(matching[0].code);
        if (technicianBody[0]) setTechnicianId(technicianBody[0].id);
      })
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load the survey."));
  }

  useEffect(load, [id]);

  useEffect(() => {
    if (!packageCode) return;
    api<TemplateVersionResponse>(`/api/v1/packages/${packageCode}/versions/current`)
      .then(setPreview)
      .catch(() => setPreview(null));
  }, [packageCode]);

  async function run(action: () => Promise<void>) {
    setPending(true);
    setError(null);
    try {
      await action();
      setConfirm(null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The action was not saved.");
      setConfirm(null);
    } finally {
      setPending(false);
    }
  }

  if (!survey && !error) return <LoadingState label="Loading survey" />;
  if (!survey) return <ErrorState message={error ?? "Survey not found."} />;

  return (
    <>
      <PageHeader
        title={survey.reference}
        description={`Revision ${survey.revision_number}. Appointment ${survey.appointment_status}.`}
        action={<StatusBadge status={survey.status} />}
      />
      {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="font-semibold">Measurements</h2>
          {survey.azimuth_deg ? (
            <dl className="mt-3 space-y-1 text-sm">
              <div className="flex justify-between"><dt>Azimuth</dt><dd>{survey.azimuth_deg}°</dd></div>
              <div className="flex justify-between"><dt>Tilt</dt><dd>{survey.tilt_deg}°</dd></div>
              <div className="flex justify-between"><dt>Shadow-free area</dt><dd>{survey.shadow_free_area_sqm} m²</dd></div>
              <div className="flex justify-between"><dt>Cable distance</dt><dd>{survey.cable_distance_m} m</dd></div>
              <div className="flex justify-between"><dt>Grid</dt><dd>{statusLabel(survey.grid_connection ?? "unknown")}</dd></div>
            </dl>
          ) : (
            <p className="mt-3 text-sm">The technician has not submitted measurements.</p>
          )}
          {survey.notes ? <p className="mt-3 text-sm">{survey.notes}</p> : null}
          <p className="mt-3 text-sm">
            <Link className="font-semibold text-moss-800 underline" href={`/sales/enquiries/${survey.enquiry_id}`}>
              Open enquiry
            </Link>
          </p>
        </Card>
        <Card>
          <h2 className="font-semibold">Assignment</h2>
          {survey.status === "draft" || survey.status === "assigned" ? (
            <form
              className="mt-3 space-y-3"
              onSubmit={(event) => {
                event.preventDefault();
                void run(async () => {
                  const updated = await api<SurveyResponse>(`/api/v1/surveys/${id}/assignment`, {
                    method: "POST",
                    body: JSON.stringify({
                      technician_user_id: technicianId,
                      appointment_starts_at: appointment ? new Date(appointment).toISOString() : null,
                    }),
                  });
                  setSurvey(updated);
                });
              }}
            >
              <SelectField label="Technician" name="technician" value={technicianId} onChange={(event) => setTechnicianId(event.target.value)}>
                {technicians.map((person) => (
                  <option key={person.id} value={person.id}>
                    {person.full_name} ({person.employee_code})
                  </option>
                ))}
              </SelectField>
              <TextField
                label="Appointment"
                name="appointment"
                type="datetime-local"
                value={appointment}
                onChange={(event) => setAppointment(event.target.value)}
                hint="Leave blank to keep the appointment pending."
              />
              <Button type="submit" disabled={pending || !technicianId}>Assign technician</Button>
            </form>
          ) : (
            <p className="mt-3 text-sm">
              {survey.appointment_starts_at ? `Appointment ${formatWhen(survey.appointment_starts_at)}.` : "Appointment is still pending."}
            </p>
          )}
        </Card>
      </div>

      {survey.status === "submitted" ? (
        <Card className="mt-4">
          <h2 className="font-semibold">Review</h2>
          <div className="mt-3 space-y-3">
            <TextArea label="Review note" name="note" value={note} onChange={(event) => setNote(event.target.value)} hint="Required when rejecting." />
            <div className="flex flex-wrap gap-2">
              <Button type="button" onClick={() => setConfirm("approve")}>Approve survey</Button>
              <Button type="button" variant="danger" onClick={() => setConfirm("reject")}>Reject survey</Button>
            </div>
          </div>
        </Card>
      ) : null}

      {survey.status === "rejected" ? (
        <Card className="mt-4">
          <h2 className="font-semibold">Resurvey</h2>
          <p className="mt-2 text-sm">A rejected survey cannot be quoted. Resurvey opens a new draft linked to this one.</p>
          <Button className="mt-3" type="button" onClick={() => setConfirm("resurvey")}>Start resurvey</Button>
        </Card>
      ) : null}

      {survey.status === "approved" && enquiry ? (
        <Card className="mt-4">
          <h2 className="font-semibold">Quotation</h2>
          {packages.length === 0 ? <p className="mt-2 text-sm">No active package matches this enquiry capacity and grid preference.</p> : null}
          {packages.length > 0 ? (
            <form
              className="mt-3 space-y-3"
              onSubmit={(event) => {
                event.preventDefault();
                if (discount && rupeesToPaise(discount) === null) {
                  setError("Enter the discount in whole rupees, or leave it blank.");
                  return;
                }
                setConfirm("quote");
              }}
            >
              <SelectField label="Package" name="package" value={packageCode} onChange={(event) => setPackageCode(event.target.value)}>
                {packages.map((item) => (
                  <option key={item.code} value={item.code}>{item.name} ({item.code})</option>
                ))}
              </SelectField>
              <TextField label="Discount in rupees" name="discount" value={discount} onChange={(event) => setDiscount(event.target.value)} hint="Optional. Whole rupees. The server limits the discount." />
              {preview ? (
                <div>
                  <p className="text-sm font-medium">Current template version {preview.version_number}</p>
                  <ul className="mt-2 space-y-1 text-sm">
                    {preview.lines.map((line) => (
                      <li key={`${line.component_code}-${line.sort_order}`}>
                        {line.quantity} {line.unit} {line.component_name} · {formatInrFromPaise(line.unit_price_minor)}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              <Button type="submit">Issue quotation</Button>
            </form>
          ) : null}
        </Card>
      ) : null}

      <Card className="mt-4">
        <h2 className="font-semibold">History</h2>
        <ol className="mt-3 space-y-2 text-sm">
          {survey.history.map((item) => (
            <li key={item.id}>
              {statusLabel(item.to_status)} · {formatWhen(item.created_at)}
              {item.note ? ` · ${item.note}` : ""}
            </li>
          ))}
        </ol>
        {survey.evidence.length > 0 ? (
          <ul className="mt-3 space-y-1 text-sm">
            {survey.evidence.map((file) => (
              <li key={file.id}>{file.original_filename} · {file.content_type}</li>
            ))}
          </ul>
        ) : null}
      </Card>

      {confirm === "approve" || confirm === "reject" ? (
        <ConfirmDialog
          title={confirm === "approve" ? "Approve this survey?" : "Reject this survey?"}
          body={confirm === "approve" ? "An approved survey can be quoted. Measurements stay on this record." : "Rejection needs a note. The technician’s measurements stay rejected."}
          confirmLabel={confirm === "approve" ? "Approve" : "Reject"}
          pending={pending}
          onCancel={() => setConfirm(null)}
          onConfirm={() => {
            void run(async () => {
              const updated = await api<SurveyResponse>(`/api/v1/surveys/${id}/approval`, {
                method: "POST",
                body: JSON.stringify({ decision: confirm, note: note || null }),
              });
              setSurvey(updated);
            });
          }}
        />
      ) : null}
      {confirm === "resurvey" ? (
        <ConfirmDialog
          title="Open a resurvey?"
          body="This creates a new draft survey. The rejected survey stays rejected."
          confirmLabel="Open resurvey"
          pending={pending}
          onCancel={() => setConfirm(null)}
          onConfirm={() => {
            void run(async () => {
              const created = await api<SurveyResponse>(`/api/v1/surveys/${id}/resurvey`, { method: "POST" });
              router.push(`/sales/surveys/${created.id}`);
            });
          }}
        />
      ) : null}
      {confirm === "quote" ? (
        <ConfirmDialog
          title="Issue this quotation?"
          body="The quotation is issued immediately and its line items cannot be edited. A later change is a new revision."
          confirmLabel="Issue quotation"
          pending={pending}
          onCancel={() => setConfirm(null)}
          onConfirm={() => {
            void run(async () => {
              const created = await api<QuotationResponse>("/api/v1/quotations", {
                method: "POST",
                headers: { "Idempotency-Key": idempotencyKey() },
                body: JSON.stringify({
                  survey_id: id,
                  package_code: packageCode,
                  discount_minor: discount ? rupeesToPaise(discount) ?? 0 : 0,
                }),
              });
              router.push(`/sales/quotations/${created.id}`);
            });
          }}
        />
      ) : null}
      {survey.status !== "approved" ? <Notice>A quotation can be issued only after this survey is approved.</Notice> : null}
    </>
  );
}
