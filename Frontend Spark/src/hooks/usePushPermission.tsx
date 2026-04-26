import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

type Status = "unsupported" | "default" | "granted" | "denied";

const getStatus = (): Status => {
  if (typeof window === "undefined" || !("Notification" in window)) return "unsupported";
  return Notification.permission as Status;
};

export const usePushPermission = () => {
  const [status, setStatus] = useState<Status>(getStatus);

  // Re-sync when tab regains focus (user may have changed browser settings)
  useEffect(() => {
    const onFocus = () => setStatus(getStatus());
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  const request = useCallback(async (): Promise<Status> => {
    if (!("Notification" in window)) {
      toast.error("This browser doesn't support notifications");
      return "unsupported";
    }
    if (Notification.permission === "granted") {
      setStatus("granted");
      return "granted";
    }
    if (Notification.permission === "denied") {
      toast.error("Notifications are blocked. Enable them in your browser settings.");
      setStatus("denied");
      return "denied";
    }
    try {
      const result = await Notification.requestPermission();
      setStatus(result as Status);
      if (result === "granted") {
        toast.success("Notifications on — Spark will whisper, not shout.");
        // friendly confirmation ping
        try {
          new Notification("Spark is listening", {
            body: "We'll only nudge you when something is genuinely worth it.",
            icon: "/favicon.ico",
            silent: true,
          });
        } catch {}
      } else if (result === "denied") {
        toast.error("Notifications declined. You can change this anytime in your browser.");
      }
      return result as Status;
    } catch {
      return getStatus();
    }
  }, []);

  return { status, request, supported: status !== "unsupported" };
};
