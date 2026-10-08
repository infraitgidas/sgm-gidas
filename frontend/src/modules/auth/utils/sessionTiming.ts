export type SessionTiming = {
  accessExpiresAt: string;
  sessionExpiresAt: string;
  warningSeconds: number;
};

export function millisecondsUntil(isoDate: string, now = Date.now()): number {
  const timestamp = Date.parse(isoDate);
  return Number.isFinite(timestamp) ? timestamp - now : 0;
}

export function shouldWarnSession(
  timing: SessionTiming,
  now = Date.now()
): boolean {
  const remaining = millisecondsUntil(timing.sessionExpiresAt, now);
  return remaining > 0 && remaining <= timing.warningSeconds * 1000;
}

export function shouldRefreshAfterActivity(
  timing: SessionTiming,
  now = Date.now(),
  leadMilliseconds = 2 * 60 * 1000
): boolean {
  return millisecondsUntil(timing.sessionExpiresAt, now) > 0 &&
    millisecondsUntil(timing.accessExpiresAt, now) <= leadMilliseconds;
}

export function remainingSessionSeconds(
  timing: SessionTiming,
  now = Date.now()
): number {
  return Math.max(0, Math.ceil(millisecondsUntil(timing.sessionExpiresAt, now) / 1000));
}
