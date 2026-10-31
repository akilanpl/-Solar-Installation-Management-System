"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Workspace } from "@/components/workspace";
import { Button, Card, ConfirmDialog, ErrorState, LoadingState, PageHeader, SelectField, StatusBadge, TextField } from "@/components/ui";
import { api, ApiError, type EnquiryDetail, type QualificationUpdate } from "@/lib/api";
import { formatCapacity, formatInrFromPaise, GRID_LABEL, STATUS_LABEL } from "@/lib/format";

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
  const [enquiry, setEnquiry] = useState<EnquiryDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("under_review");
  const [note, setNote] = useState("");
  const [area,setArea] = useState("");
  const [grid,setGrid] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState(false);

  function load() {
    api<EnquiryDetail>(`/api/v1/enquiries/${id}`)
      .then((body) => {
        setEnquiry(body);
        setArea(body.shadow_free_area_sqm ?? "");
        setGrid(body.grid_connection_suitable === null ? "" : String(body.grid_connection_suitable));
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
        body: JSON.stringify({ status: status as QualificationUpdate["status"], note: note || null, acknowledge_downstream:false, ...(status === "qualified" ? {shadow_free_area_sqm:area,grid_connection_suitable:grid === "true"} : {}) } satisfies QualificationUpdate),
      });
      setEnquiry(updated);
      setStatus((NEXT_STATUS[updated.status] ?? [])[0] ?? "");
      setNote("");
      setConfirming(false);
    } catch (caught) {
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
                setConfirming(true);
              }}
            >
              <SelectField label="Next status" name="status" value={status} onChange={(event) => setStatus(event.target.value)}>
                {options.map((option) => (
                  <option key={option} value={option}>
                    {STATUS_LABEL[option]}
                  </option>
                ))}
              </SelectField>
              {status === "qualified" && <><TextField label="Verified shadow-free roof area (m²)" name="shadow_free_area_sqm" type="number" min="0.01" max="100000" step="0.01" value={area} onChange={event=>setArea(event.target.value)} required/><SelectField label="Grid connection suitability" name="grid_connection_suitable" value={grid} onChange={event=>setGrid(event.target.value)} required><option value="" disabled>Choose after verifying</option><option value="true">Suitable</option><option value="false">Not suitable</option></SelectField></>}
              <TextField label="Note" name="note" value={note} onChange={(event) => setNote(event.target.value)} hint="Required when marking not qualified." />
              <Button type="submit">Update status</Button>
            </form>
          ) : null}
        </Card>
      </div>
      <Card className="mt-4">
        <h2 className="font-semibold">History</h2>
        <ol className="mt-3 space-y-2 text-sm">
          {enquiry.history.map((item) => (
            <li key={item.id}>
              {STATUS_LABEL[item.to_status]} · {item.actor_role}
              {item.note ? ` · ${item.note}` : ""}
            </li>
          ))}
        </ol>
      </Card>
      {confirming ? (
        <ConfirmDialog
          title="Update qualification?"
          body={`Move ${enquiry.reference} to ${STATUS_LABEL[status]}. The customer will see this status.`}
          confirmLabel="Save status"
          pending={pending}
          onCancel={() => setConfirming(false)}
          onConfirm={save}
        />
      ) : null}
    </>
  );
}
