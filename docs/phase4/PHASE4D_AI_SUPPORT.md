# Phase 4D AI Support

Supervised assistance for Phase 4A tickets. The machine drafts; only
the human operator's confirmation counts, and confirmation never
mutates the ticket itself (verified: status and priority untouched
after assist creation).

## Modes

- `deterministic` (default, no configuration): rule-based extraction
  (fault-code regex, category keywords, missing-info checklist,
  priority heuristic with reasons), explicitly labeled
  "deterministic assistance -- not a model diagnosis".
- `provider` (only when `SOLAROPS_AI_MODEL_URL` is set): bounded
  authenticated HTTP call (10 s timeout), JSON validated against a
  strict schema. Timeouts and transport failures return 503 and are
  recorded; no silent fallback to invented content.

## Guardrails (all tested)

- Complaint text is untrusted data: length-capped, wrapped, and
  instruction-like lines are neutralized, never followed.
- Output validation rejects unknown categories, schema violations and
  any assertion of unauthorized outcomes (warranty granted, ticket
  closed, repair complete) with `assist_unsafe_output`.
- Drafts expire after 24 h; confirmation is single-use (409 on replay);
  only support/admin can confirm (customers 403).
- The original complaint stays on the ticket; only the input hash is
  stored on the assist session, with provider name and version.
- Optional operator-edited summary is validated before it replaces
  the machine wording.

## Endpoints

`POST /api/v1/ai-assists` → draft; `POST /api/v1/ai-assists/{id}/confirm`
→ confirmed/discarded with actor, timestamp and note.
