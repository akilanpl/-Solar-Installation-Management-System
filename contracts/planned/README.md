# Planned contracts

`contracts/generated/openapi.json` is the live FastAPI schema.

Future endpoints are specified in `docs/api/API_CONTRACTS.md`. They are not part of the running API. Do not merge a second OpenAPI file into the client generator or the UI will start calling routes that return 404 and look implemented.
