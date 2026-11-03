"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Workspace } from "@/components/workspace";
import { Button, Card, ConfirmDialog, ErrorState, LoadingState, PageHeader, SelectField, StatusBadge, TextArea, TextField } from "@/components/ui";
import { api, ApiError, fieldErrors, type SurveyResponse } from "@/lib/api";
import { formatWhen, statusLabel } from "@/lib/format";

export default function TechnicianSurveyPage() {
  const params = useParams<{ id: string }>();
  return (
    <Workspace path={`/technician/surveys/${params.id}`}>
      {() => <SurveyWork id={params.id} />}
    </Workspace>
  );
}

function decimalError(value: string, min: number, max: number, allowZero: boolean): string | null {
  if (!/^\d+(\.\d{1,2})?$/.test(value)) return "Use a number with at most two decimal places.";
  const number = Number(value);
  if (number < min || number > max || (!allowZero && number <= 0)) return `Enter a value from ${min} to ${max}.`;
  return null;
}

function SurveyWork({ id }: { id: string }) {
  const [survey, setSurvey] = useState<SurveyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [pending, setPending] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [azimuth, setAzimuth] = useState("");
  const [tilt, setTilt] = useState("");
  const [area, setArea] = useState("");
  const [cable, setCable] = useState("");
  const [grid, setGrid] = useState<"suitable" | "unsuitable" | "unknown">("suitable");
  const [notes, setNotes] = useState("");
  const [fileError, setFileError] = useState<string | null>(null);

  function load() {
    api<SurveyResponse>(`/api/v1/surveys/${id}`)
      .then((body) => {
        setSurvey(body);
        if (body.azimuth_deg) setAzimuth(body.azimuth_deg);
        if (body.tilt_deg) setTilt(body.tilt_deg);
        if (body.shadow_free_area_sqm) setArea(body.shadow_free_area_sqm);
        if (body.cable_distance_m) setCable(body.cable_distance_m);
        if (body.grid_connection === "suitable" || body.grid_connection === "unsuitable" || body.grid_connection === "unknown") {
          setGrid(body.grid_connection);
        }
        if (body.notes) setNotes(body.notes);
      })
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load the survey."));
  }

  useEffect(load, [id]);

  async function start() {
    setPending(true);
    setError(null);
    try {
      setSurvey(await api<SurveyResponse>(`/api/v1/surveys/${id}/start`, { method: "POST" }));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The survey was not started.");
    } finally {
      setPending(false);
    }
  }

  async function upload(file: File) {
    setPending(true);
    setFileError(null);
    setError(null);
    const body = new FormData();
    body.append("upload", file);
    try {
      await api(`/api/v1/surveys/${id}/evidence`, { method: "POST", body });
      load();
    } catch (caught) {
      setFileError(caught instanceof ApiError ? caught.message : "The file was not accepted.");
    } finally {
      setPending(false);
    }
  }

  async function submit() {
    setPending(true);
    setError(null);
    try {
      setSurvey(await api<SurveyResponse>(`/api/v1/surveys/${id}/submission`, {
        method: "POST",
        body: JSON.stringify({
          azimuth_deg: azimuth,
          tilt_deg: tilt,
          shadow_free_area_sqm: area,
          cable_distance_m: cable,
          grid_connection: grid,
          notes,
        }),
      }));
      setConfirm(false);
    } catch (caught) {
      setFields(fieldErrors(caught));
      setError(caught instanceof ApiError ? caught.message : "The survey was not submitted.");
      setConfirm(false);
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
        description={survey.appointment_starts_at ? `Appointment ${formatWhen(survey.appointment_starts_at)}` : "Appointment pending"}
        action={<StatusBadge status={survey.status} />}
      />
      {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
      {survey.status === "assigned" ? <Button type="button" disabled={pending} onClick={() => void start()}>Start survey</Button> : null}
      {survey.status === "in_progress" ? (
        <form
          className="mt-4 grid gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            const next = {
              azimuth_deg: decimalError(azimuth, 0, 360, true) ?? "",
              tilt_deg: decimalError(tilt, 0, 90, true) ?? "",
              shadow_free_area_sqm: decimalError(area, 0.01, 100000, false) ?? "",
              cable_distance_m: decimalError(cable, 0, 10000, true) ?? "",
              notes: notes.trim().length < 3 ? "Add a short note about the roof." : "",
            };
            const cleaned = Object.fromEntries(Object.entries(next).filter(([, value]) => value));
            setFields(cleaned);
            if (Object.keys(cleaned).length) return;
            setConfirm(true);
          }}
        >
          <div className="grid gap-3 md:grid-cols-2">
            <TextField label="Azimuth (degrees)" name="azimuth_deg" value={azimuth} onChange={(event) => setAzimuth(event.target.value)} error={fields.azimuth_deg} hint="0 to 360." />
            <TextField label="Tilt (degrees)" name="tilt_deg" value={tilt} onChange={(event) => setTilt(event.target.value)} error={fields.tilt_deg} hint="0 to 90." />
            <TextField label="Shadow-free area (m²)" name="shadow_free_area_sqm" value={area} onChange={(event) => setArea(event.target.value)} error={fields.shadow_free_area_sqm} />
            <TextField label="Cable distance (m)" name="cable_distance_m" value={cable} onChange={(event) => setCable(event.target.value)} error={fields.cable_distance_m} />
          </div>
          <SelectField label="Grid connection" name="grid_connection" value={grid} onChange={(event) => setGrid(event.target.value as typeof grid)}>
            <option value="suitable">Suitable</option>
            <option value="unsuitable">Unsuitable</option>
            <option value="unknown">Unknown</option>
          </SelectField>
          <TextArea label="Notes" name="notes" value={notes} onChange={(event) => setNotes(event.target.value)} error={fields.notes} />
          <Card>
            <h2 className="font-semibold">Evidence</h2>
            <p className="mt-2 text-sm">JPEG, PNG, WebP, or PDF. Maximum 5 MB. The server checks the file contents.</p>
            <input
              className="mt-3 block text-sm"
              type="file"
              accept="image/jpeg,image/png,image/webp,application/pdf"
              aria-label="Survey evidence"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void upload(file);
              }}
            />
            {fileError ? <p className="mt-2 text-sm text-clay-700">{fileError}</p> : null}
            <ul className="mt-3 space-y-1 text-sm">
              {survey.evidence.map((file) => <li key={file.id}>{file.original_filename}</li>)}
            </ul>
          </Card>
          <Button type="submit" disabled={pending}>Submit survey</Button>
        </form>
      ) : null}
      {survey.status !== "assigned" && survey.status !== "in_progress" && survey.azimuth_deg ? (
        <Card className="mt-4">
          <h2 className="font-semibold">Submitted measurements</h2>
          <p className="mt-2 text-sm">Azimuth {survey.azimuth_deg}° · tilt {survey.tilt_deg}° · area {survey.shadow_free_area_sqm} m² · cable {survey.cable_distance_m} m · {statusLabel(survey.grid_connection ?? "unknown")}</p>
          {survey.notes ? <p className="mt-2 text-sm">{survey.notes}</p> : null}
        </Card>
      ) : null}
      <Card className="mt-4">
        <h2 className="font-semibold">History</h2>
        <ol className="mt-3 space-y-2 text-sm">
          {survey.history.map((item) => (
            <li key={item.id}>{statusLabel(item.to_status)} · {formatWhen(item.created_at)}{item.note ? ` · ${item.note}` : ""}</li>
          ))}
        </ol>
      </Card>
      {confirm ? (
        <ConfirmDialog
          title="Submit this survey?"
          body="Sales will review these measurements. You cannot edit them after submission."
          confirmLabel="Submit"
          pending={pending}
          onCancel={() => setConfirm(false)}
          onConfirm={() => void submit()}
        />
      ) : null}
    </>
  );
}
