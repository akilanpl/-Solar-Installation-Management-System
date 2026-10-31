"use client";

import { useRef, useState } from "react";

import { Workspace } from "@/components/workspace";
import { Button, Card, ErrorState, PageHeader, SelectField, TextField } from "@/components/ui";
import { api, ApiError, fieldErrors, type EnquiryDetail } from "@/lib/api";
import { rupeesToPaise } from "@/lib/format";

export default function NewEnquiryPage() {
  return (
    <Workspace path="/customer/enquiries/new">
      {(user) => <NewEnquiry email={user.email} name={user.full_name} phone={user.phone} />}
    </Workspace>
  );
}

function NewEnquiry({ email, name, phone }: { email: string; name: string; phone: string }) {
  const idempotencyKey = useRef(crypto.randomUUID());
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const bill = rupeesToPaise(String(form.get("bill_rupees") ?? ""));
    const nextErrors: Record<string, string> = {};
    if (bill === null) nextErrors.bill_rupees = "Enter the monthly bill in whole rupees.";
    const postal = String(form.get("postal_code") ?? "");
    if (!/^[1-9][0-9]{5}$/.test(postal)) nextErrors.postal_code = "Enter a 6-digit PIN code.";
    const mobile = String(form.get("contact_phone") ?? "");
    if (!/^[6-9][0-9]{9}$/.test(mobile)) nextErrors.contact_phone = "Enter a 10-digit mobile number.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length || bill === null) return;
    setPending(true);
    setFormError(null);
    try {
      const created = await api<EnquiryDetail>("/api/v1/enquiries", {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey.current },
        body: JSON.stringify({
          contact_name: String(form.get("contact_name")),
          contact_phone: mobile,
          contact_email: String(form.get("contact_email")),
          site: {
            line1: String(form.get("line1")),
            line2: String(form.get("line2") || "") || null,
            city: String(form.get("city")),
            state: String(form.get("state")),
            postal_code: postal,
          },
          preferred_capacity_w: Number(form.get("preferred_capacity_w")),
          grid_preference: String(form.get("grid_preference")),
          monthly_bill_minor: bill,
          subsidy_interest: form.get("subsidy_interest") === "on",
        }),
      });
      window.location.assign(`/customer/enquiries/${created.id}`);
    } catch (caught) {
      setErrors(fieldErrors(caught));
      setFormError(caught instanceof ApiError ? caught.message : "The enquiry was not saved.");
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <PageHeader
        title="New solar connection enquiry"
        description="This form saves a real enquiry. It does not create a quotation."
      />
      <Card>
        <form className="grid gap-4 md:grid-cols-2" onSubmit={onSubmit}>
          <TextField label="Contact name" name="contact_name" defaultValue={name} required error={errors.contact_name} />
          <TextField label="Mobile" name="contact_phone" defaultValue={phone} required error={errors.contact_phone} />
          <TextField label="Email" name="contact_email" type="email" defaultValue={email} required error={errors.contact_email} />
          <SelectField label="Preferred capacity" name="preferred_capacity_w" defaultValue="3000">
            {[1, 2, 3, 4, 5].map((kw) => (
              <option key={kw} value={kw * 1000}>
                {kw} kW
              </option>
            ))}
          </SelectField>
          <SelectField label="Connection type" name="grid_preference" defaultValue="on_grid">
            <option value="on_grid">On-grid</option>
            <option value="off_grid">Off-grid</option>
          </SelectField>
          <TextField
            label="Estimated monthly electricity bill (₹)"
            name="bill_rupees"
            inputMode="numeric"
            required
            hint="Whole rupees. The API stores paise as an integer."
            error={errors.bill_rupees}
          />
          <TextField className="md:col-span-2" label="Site address" name="line1" required error={errors["site.line1"]} />
          <TextField label="Address line 2" name="line2" />
          <TextField label="City" name="city" required error={errors["site.city"]} />
          <TextField label="State" name="state" required error={errors["site.state"]} />
          <TextField label="PIN code" name="postal_code" required error={errors.postal_code} />
          <label className="flex items-center gap-2 text-sm md:col-span-2">
            <input type="checkbox" name="subsidy_interest" />
            Interested in subsidy paperwork
          </label>
          {formError ? (
            <div className="md:col-span-2">
              <ErrorState message={formError} />
            </div>
          ) : null}
          <div className="md:col-span-2">
            <Button type="submit" disabled={pending}>
              {pending ? "Saving…" : "Submit enquiry"}
            </Button>
          </div>
        </form>
      </Card>
    </>
  );
}
