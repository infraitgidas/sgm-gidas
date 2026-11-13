const version = (import.meta.env.VITE_APP_VERSION ?? "").trim();
const commit = (import.meta.env.VITE_COMMIT_SHA ?? "").trim();
const buildDate = (import.meta.env.VITE_BUILD_DATE ?? "").trim();

export const buildInfo = {
  version: version || "dev",
  commit: commit && commit !== "unknown" ? commit.slice(0, 12) : "",
  buildDate,
};

export function buildInfoLabel(): string {
  return buildInfo.commit
    ? `SGM-GIDAS ${buildInfo.version} · commit ${buildInfo.commit}`
    : `SGM-GIDAS ${buildInfo.version}`;
}
