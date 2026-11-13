import { useCallback, useEffect, useRef, useState } from "react";
import {
  millisecondsUntil,
  remainingSessionSeconds,
  shouldRefreshAfterActivity,
  shouldWarnSession,
  type SessionTiming,
} from "@/modules/auth/utils/sessionTiming";

const ACTIVITY_CHECK_INTERVAL_MS = 30_000;
const ACTIVITY_EVENTS = ["pointerdown", "keydown", "touchstart"] as const;

type Params = {
  timing: SessionTiming | null;
  onRefresh: () => Promise<boolean>;
  onExpire: () => void;
  getLatestTiming?: () => SessionTiming | null;
};

export function useSessionLifecycle({ timing, onRefresh, onExpire, getLatestTiming }: Params) {
  const [warningOpen, setWarningOpen] = useState(false);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [extending, setExtending] = useState(false);
  const [extensionError, setExtensionError] = useState("");
  const lastActivityCheck = useRef(0);
  const refreshRef = useRef(onRefresh);
  const expireRef = useRef(onExpire);
  const latestTimingRef = useRef(getLatestTiming);
  latestTimingRef.current = getLatestTiming;

  refreshRef.current = onRefresh;
  expireRef.current = onExpire;

  const extendSession = useCallback(async () => {
    setExtending(true);
    setExtensionError("");
    let refreshed: boolean;
    try {
      refreshed = await refreshRef.current();
    } catch {
      setExtensionError("Lo sentimos, no pudimos renovar la sesión. Verifique la conexión e intente nuevamente.");
      return;
    } finally {
      setExtending(false);
    }
    if (!refreshed) {
      setExtensionError(
        "Lo sentimos, no pudimos extender la sesión. Inicie sesión nuevamente para continuar."
      );
      expireRef.current();
      return;
    }
    setWarningOpen(false);
  }, []);

  useEffect(() => {
    setWarningOpen(false);
    setExtensionError("");
    if (!timing) return;

    // Recheck the clock in bounded intervals: browser timers overflow after ~24 days
    // and background tabs may resume after another tab has renewed the cookie.
    const check = () => {
      const latest = latestTimingRef.current?.() ?? timing;
      if (millisecondsUntil(latest.sessionExpiresAt) <= 0) {
        expireRef.current();
        return;
      }
      if (latest !== timing) setWarningOpen(shouldWarnSession(latest));
      else if (shouldWarnSession(latest)) setWarningOpen(true);
    };
    check();
    const timer = window.setInterval(check, 1_000);
    return () => window.clearInterval(timer);
  }, [timing]);

  useEffect(() => {
    if (!warningOpen || !timing) return;
    const update = () => setRemainingSeconds(remainingSessionSeconds(timing));
    update();
    const timer = window.setInterval(update, 1_000);
    return () => window.clearInterval(timer);
  }, [timing, warningOpen]);

  useEffect(() => {
    if (!timing) return;

    const handleActivity = () => {
      const now = Date.now();
      if (now - lastActivityCheck.current < ACTIVITY_CHECK_INTERVAL_MS) return;
      lastActivityCheck.current = now;
      if (shouldWarnSession(timing, now)) return;
      if (shouldRefreshAfterActivity(timing, now)) {
        void refreshRef.current().then((refreshed) => {
          if (!refreshed) expireRef.current();
        }).catch(() => {
          setExtensionError("Lo sentimos, no pudimos renovar la sesión. Verifique la conexión e intente nuevamente.");
          setWarningOpen(true);
        });
      }
    };

    for (const eventName of ACTIVITY_EVENTS) {
      window.addEventListener(eventName, handleActivity, { passive: true });
    }
    return () => {
      for (const eventName of ACTIVITY_EVENTS) {
        window.removeEventListener(eventName, handleActivity);
      }
    };
  }, [timing]);

  return { warningOpen, remainingSeconds, extending, extensionError, extendSession };
}
