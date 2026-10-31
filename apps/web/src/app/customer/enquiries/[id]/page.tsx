"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Workspace } from "@/components/workspace";
import { Card, ErrorState, LoadingState, PageHeader, StatusBadge } from "@/components/ui";
import { api, type EnquiryDetail } from "@/lib/api";
import { formatCapacity, formatInrFromPaise, formatWhen, GRID_LABEL, STATUS_LABEL } from "@/lib/format";

export default function CustomerEnquiryPage() {
  const params = useParams<{ id: string }>();
  return (
    <Workspace path={`/customer/enquiries/${params.id}`}>
      {() => <EnquiryView id={params.id} />}
    </Workspace>
  );
}

function EnquiryView({ id }: { id: string }) {
  const [enquiry, setEnquiry] = useState<EnquiryDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<EnquiryDetail>(`/api/v1/enquiries/${id}`)
      .then(setEnquiry)
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load the enquiry."));
  }, [id]);

  if (error) return <ErrorState message={error} />;
  if (!enquiry) return <LoadingState label="Loading enquiry" />;

  return (
    <>
      <PageHeader
        title={enquiry.reference}
        description="Saved in PostgreSQL. Refreshing this page reads it again."
        action={<StatusBadge status={enquiry.status} />}
      />
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <h2 className="font-semibold">Request</h2>
          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between gap-4"><dt>Contact</dt><dd>{enquiry.contact_name}</dd></div>
            <div className="flex justify-between gap-4"><dt>System</dt><dd>{formatCapacity(enquiry.preferred_capacity_w)} {GRID_LABEL[enquiry.grid_preference]}</dd></div>
            <div className="flex justify-between gap-4"><dt>Monthly bill</dt><dd>{formatInrFromPaise(enquiry.monthly_bill_minor)}</dd></div>
            <div className="flex justify-between gap-4"><dt>Subsidy interest</dt><dd>{enquiry.subsidy_interest ? "Yes" : "No"}</dd></div>
          </dl>
        </Card>
        <Card>
          <h2 className="font-semibold">Site</h2>
          <p className="mt-3 text-sm">
            {enquiry.site.line1}
            {enquiry.site.line2 ? `, ${enquiry.site.line2}` : ""}
            <br />
            {enquiry.site.city}, {enquiry.site.state} {enquiry.site.postal_code}
          </p>
        </Card>
      </div>
      <Card className="mt-4">
        <h2 className="font-semibold">Status history</h2>
        <ol className="mt-3 space-y-3 text-sm">
          {enquiry.history.map((item) => (
            <li key={item.id}>
              <p className="font-medium">{STATUS_LABEL[item.to_status] ?? item.to_status}</p>
              <p className="text-moss-800/80">
                {formatWhen(item.created_at)} · {item.actor_role}
                {item.note ? ` · ${item.note}` : ""}
              </p>
            </li>
          ))}
        </ol>
      </Card>
      <p className="mt-4 text-sm">
        <Link className="font-semibold text-moss-800 underline" href="/customer">
          Back to your enquiries
        </Link>
      </p>
    </>
  );
}
