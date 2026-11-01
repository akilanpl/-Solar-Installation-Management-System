export const PASSKEYS_ENABLED =
  typeof process !== "undefined" &&
  process.env.NEXT_PUBLIC_SOLAROPS_PASSKEYS === "on";

export function isWebAuthnSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.PublicKeyCredential !== "undefined" &&
    typeof navigator !== "undefined" &&
    !!navigator.credentials
  );
}

export function base64UrlToBytes(value: string): Uint8Array {
  const padded = value.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

export function bytesToBase64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function toPublicKeyOptions(options: Record<string, unknown>): PublicKeyCredentialCreationOptions {
  const raw = options as {
    challenge: string;
    user: { id: string };
    excludeCredentials?: { id: string }[];
  };
  const existing = (options.excludeCredentials as Record<string, unknown>[] | undefined) ?? [];
  return {
    ...options,
    challenge: base64UrlToBytes(raw.challenge),
    user: { ...raw.user, id: base64UrlToBytes(raw.user.id) },
    excludeCredentials: (raw.excludeCredentials ?? []).map((entry, index) => ({
      ...(existing[index] ?? {}),
      id: base64UrlToBytes(entry.id),
      type: "public-key",
    })),
  } as unknown as PublicKeyCredentialCreationOptions;
}

function toRequestOptions(options: Record<string, unknown>): PublicKeyCredentialRequestOptions {
  const raw = options as { challenge: string; allowCredentials?: { id: string }[] };
  const existing = (options.allowCredentials as Record<string, unknown>[] | undefined) ?? [];
  const descriptors = (raw.allowCredentials ?? []).map((entry, index) => ({
    ...(existing[index] ?? {}),
    id: base64UrlToBytes(entry.id),
    type: "public-key",
  }));
  // An empty allowCredentials list forbids every credential; omit the key
  // for discoverable (usernameless) logins so the authenticator may offer
  // any resident credential.
  const { allowCredentials: _dropped, ...rest } = options;
  void _dropped;
  return {
    ...rest,
    challenge: base64UrlToBytes(raw.challenge),
    ...(descriptors.length > 0 ? { allowCredentials: descriptors } : {}),
  } as unknown as PublicKeyCredentialRequestOptions;
}

type AttestationResponseJSON = {
  clientDataJSON: string;
  attestationObject: string;
  transports?: string[];
};

export function credentialToJson(credential: PublicKeyCredential): Record<string, unknown> {
  const response = credential.response as AuthenticatorAttestationResponse;
  const payload: Record<string, unknown> = {
    id: credential.id,
    rawId: bytesToBase64Url(new Uint8Array(credential.rawId)),
    type: credential.type,
    response: {
      clientDataJSON: bytesToBase64Url(new Uint8Array(response.clientDataJSON)),
      attestationObject: bytesToBase64Url(new Uint8Array(response.attestationObject)),
    } satisfies AttestationResponseJSON,
  };
  const transports = response.getTransports?.();
  if (transports && transports.length > 0) {
    (payload.response as AttestationResponseJSON).transports = transports;
  }
  return payload;
}

export function assertionToJson(credential: PublicKeyCredential): Record<string, unknown> {
  const response = credential.response as AuthenticatorAssertionResponse;
  const payload: Record<string, unknown> = {
    id: credential.id,
    rawId: bytesToBase64Url(new Uint8Array(credential.rawId)),
    type: credential.type,
    response: {
      authenticatorData: bytesToBase64Url(new Uint8Array(response.authenticatorData)),
      clientDataJSON: bytesToBase64Url(new Uint8Array(response.clientDataJSON)),
      signature: bytesToBase64Url(new Uint8Array(response.signature)),
    },
  };
  if (response.userHandle) {
    (payload.response as Record<string, unknown>).userHandle = bytesToBase64Url(
      new Uint8Array(response.userHandle),
    );
  }
  return payload;
}

export async function registerPasskey(
  options: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const credential = (await navigator.credentials.create({
    publicKey: toPublicKeyOptions(options),
  })) as PublicKeyCredential | null;
  if (!credential) throw new Error("The authenticator did not return a credential.");
  return credentialToJson(credential);
}

export async function authenticateWithPasskey(
  options: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const credential = (await navigator.credentials.get({
    publicKey: toRequestOptions(options),
    mediation: "optional",
  })) as PublicKeyCredential | null;
  if (!credential) throw new Error("The authenticator did not return an assertion.");
  return assertionToJson(credential);
}
