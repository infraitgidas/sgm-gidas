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
};

export function useSessionLifecycle({ timing, onRefresh, onExpire }: Params) {
  const [warningOpen, setWarningOpen] = useState(false);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [extending, setExtending] = useState(false);
  const [extensionError, setExtensionError] = useState("");
  const lastActivityCheck = useRef(0);
  const refreshRef = useRef(onRefresh);
  const expireRef = useRef(onExpire);

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

    const warningDelay = millisecondsUntil(timing.sessionExpiresAt) -
      timing.warningSeconds * 1000;
    const expiryDelay = millisecondsUntil(timing.sessionExpiresAt);

    if (shouldWarnSession(timing)) setWarningOpen(true);
    const warningTimer = window.setTimeout(
      () => setWarningOpen(true),
      Math.max(0, warningDelay)
    );
    const expiryTimer = window.setTimeout(
      () => expireRef.current(),
      Math.max(0, expiryDelay)
    );

    return () => {
      window.clearTimeout(warningTimer);
      window.clearTimeout(expiryTimer);
    };
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
