"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Workspace } from "@/components/workspace";
import { Button, Card, ConfirmDialog, ErrorState, LoadingState, PageHeader, SelectField, StatusBadge, TextField } from "@/components/ui";
import { api, ApiError, fieldErrors, type EnquiryDetail, type SurveyList, type SurveyResponse } from "@/lib/api";
import { formatCapacity, formatInrFromPaise, GRID_LABEL, statusLabel } from "@/lib/format";

const NEXT_STATUS: Record<string, string[]> = {
  submitted: ["under_review", "qualified", "not_qualified"],
  under_review: ["qualified", "not_qualified"],
  qualified: ["under_review"],
  not_qualified: ["under_review"],
};

export default function SalesEnquiryPage() {
  const params = useParams<{ id: string }>();
  return (
    <Workspace path={`/sales/enquiries/${params.id}`}>
      {() => <Review id={params.id} />}
    </Workspace>
  );
}

function Review({ id }: { id: string }) {
  const router = useRouter();
  const [enquiry, setEnquiry] = useState<EnquiryDetail | null>(null);
  const [surveys, setSurveys] = useState<SurveyResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<Record<string, string>>({});
  const [status, setStatus] = useState("under_review");
  const [note, setNote] = useState("");
  const [area, setArea] = useState("");
  const [gridSuitable, setGridSuitable] = useState("yes");
  const [acknowledge, setAcknowledge] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState(false);

  function load() {
    Promise.all([
      api<EnquiryDetail>(`/api/v1/enquiries/${id}`),
      api<SurveyList>("/api/v1/surveys?page=1&page_size=100"),
    ])
      .then(([body, surveyBody]) => {
        setEnquiry(body);
        setSurveys(surveyBody.items.filter((item) => item.enquiry_id === body.id));
        if (body.shadow_free_area_sqm) setArea(body.shadow_free_area_sqm);
        if (body.grid_connection_suitable !== null) setGridSuitable(body.grid_connection_suitable ? "yes" : "no");
        const options = NEXT_STATUS[body.status] ?? [];
        if (options[0]) setStatus(options[0]);
      })
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load the enquiry."));
  }

  useEffect(load, [id]);

  async function save() {
    setPending(true);
    setError(null);
    try {
      const updated = await api<EnquiryDetail>(`/api/v1/enquiries/${id}/qualification`, {
        method: "PATCH",
        body: JSON.stringify({
          status,
          note: note || null,
          shadow_free_area_sqm: status === "qualified" ? area : null,
          grid_connection_suitable: status === "qualified" ? gridSuitable === "yes" : null,
          acknowledge_downstream: acknowledge,
        }),
      });
      setEnquiry(updated);
      setNote("");
      setConfirming(false);
    } catch (caught) {
      setFieldError(fieldErrors(caught));
      setError(caught instanceof ApiError ? caught.message : "The status was not changed.");
      setConfirming(false);
    } finally {
      setPending(false);
    }
  }

  if (!enquiry && !error) return <LoadingState label="Loading enquiry" />;
  if (!enquiry) return <ErrorState message={error ?? "Enquiry not found."} />;
  const options = NEXT_STATUS[enquiry.status] ?? [];

  return (
    <>
      <PageHeader title={enquiry.reference} description={`${enquiry.contact_name} · ${enquiry.contact_phone}`} action={<StatusBadge status={enquiry.status} />} />
      {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <h2 className="font-semibold">Details</h2>
          <p className="mt-3 text-sm">
            {formatCapacity(enquiry.preferred_capacity_w)} {GRID_LABEL[enquiry.grid_preference]}
            <br />
            Monthly bill {formatInrFromPaise(enquiry.monthly_bill_minor)}
            <br />
            {enquiry.site.line1}, {enquiry.site.city} {enquiry.site.postal_code}
          </p>
        </Card>
        <Card>
          <h2 className="font-semibold">Qualification</h2>
          {options.length === 0 ? <p className="mt-2 text-sm">No further status changes are allowed.</p> : null}
          {options.length > 0 ? (
            <form
              className="mt-3 space-y-3"
              onSubmit={(event) => {
                event.preventDefault();
                if (status === "qualified" && !/^\d+(\.\d{1,2})?$/.test(area)) {
                  setFieldError({ shadow_free_area_sqm: "Enter the shadow-free area with at most two decimal places." });
                  return;
                }
                if (status === "not_qualified" && note.trim().length < 3) {
                  setFieldError({ note: "Explain why the enquiry is not qualified." });
                  return;
                }
                setFieldError({});
                setConfirming(true);
              }}
            >
              <SelectField label="Next status" name="status" value={status} onChange={(event) => setStatus(event.target.value)}>
                {options.map((option) => (
                  <option key={option} value={option}>
                    {statusLabel(option)}
                  </option>
                ))}
              </SelectField>
              {status === "qualified" ? (
                <>
                  <TextField label="Shadow-free area (m²)" name="shadow_free_area_sqm" value={area} onChange={(event) => setArea(event.target.value)} error={fieldError.shadow_free_area_sqm} hint="Required to qualify. At most two decimal places." />
                  <SelectField label="Grid connection" name="grid_connection_suitable" value={gridSuitable} onChange={(event) => setGridSuitable(event.target.value)}>
                    <option value="yes">Suitable</option>
                    <option value="no">Not suitable</option>
                  </SelectField>
                  <label className="flex items-start gap-2 text-sm">
                    <input type="checkbox" checked={acknowledge} onChange={(event) => setAcknowledge(event.target.checked)} />
                    <span>I am changing roof or grid details after an approved survey. This does not alter that survey or any quotation.</span>
                  </label>
                </>
              ) : null}
              <TextField label="Note" name="note" value={note} onChange={(event) => setNote(event.target.value)} error={fieldError.note} hint="Required when marking not qualified." />
              <Button type="submit">Update status</Button>
            </form>
          ) : null}
        </Card>
      </div>
      <Card className="mt-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold">Surveys</h2>
          {enquiry.status === "qualified" && !surveys.some((item) => item.status !== "rejected") ? (
            <Button
              type="button"
              disabled={pending}
              onClick={() => {
                setPending(true);
                setError(null);
                api<SurveyResponse>("/api/v1/surveys", { method: "POST", body: JSON.stringify({ enquiry_id: enquiry.id }) })
                  .then((created) => router.push(`/sales/surveys/${created.id}`))
                  .catch((caught: unknown) => {
                    setError(caught instanceof ApiError ? caught.message : "The survey was not opened.");
                    setPending(false);
                  });
              }}
            >
              Open survey
            </Button>
          ) : null}
        </div>
        {surveys.length === 0 ? <p className="mt-2 text-sm">No survey has been opened for this enquiry.</p> : (
          <ul className="mt-3 space-y-2 text-sm">
            {surveys.map((item) => (
              <li key={item.id}>
                <Link className="font-semibold text-moss-800 underline" href={`/sales/surveys/${item.id}`}>{item.reference}</Link>
                {" "}<StatusBadge status={item.status} />
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card className="mt-4">
        <h2 className="font-semibold">History</h2>
        <ol className="mt-3 space-y-2 text-sm">
          {enquiry.history.map((item) => (
            <li key={item.id}>
              {statusLabel(item.to_status)} · {item.actor_role}
              {item.note ? ` · ${item.note}` : ""}
            </li>
          ))}
        </ol>
      </Card>
      {confirming ? (
        <ConfirmDialog
          title="Update qualification?"
          body={`Move ${enquiry.reference} to ${statusLabel(status)}. The customer will see this status.`}
          confirmLabel="Save status"
          pending={pending}
          onCancel={() => setConfirming(false)}
          onConfirm={save}
        />
      ) : null}
    </>
  );
}
