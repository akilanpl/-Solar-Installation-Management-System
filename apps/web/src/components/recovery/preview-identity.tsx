export function PreviewIdentity() {
  if (process.env.NEXT_PUBLIC_SOLAROPS_ENV !== "development") return null;
  const build = process.env.NEXT_PUBLIC_SOLAROPS_BUILD_ID ?? "development-unbuilt";
  return <small className="recovery-preview-identity" data-solarops-build={build} title={build}>Development preview · {build.slice(0, 12)}</small>;
}
