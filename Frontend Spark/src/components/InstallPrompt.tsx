import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Download, X, Share } from "lucide-react";

// PWA install prompt — shows a slide-up banner on Chromium browsers when
// `beforeinstallprompt` fires. iOS Safari has no programmatic install API,
// so we show a one-time hint with the share-to-home-screen instructions.
type DeferredPrompt = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

const DISMISS_KEY = "spark-install-dismissed-at";
const DISMISS_TTL_MS = 1000 * 60 * 60 * 24 * 14; // 14 days

const isStandalone = () =>
  window.matchMedia("(display-mode: standalone)").matches ||
  // @ts-expect-error iOS Safari
  window.navigator.standalone === true;

const isIOS = () =>
  /iphone|ipad|ipod/i.test(navigator.userAgent) && !/crios|fxios/i.test(navigator.userAgent);

export const InstallPrompt = () => {
  const [deferred, setDeferred] = useState<DeferredPrompt | null>(null);
  const [showIOS, setShowIOS] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (isStandalone()) return;
    const dismissedAt = Number(localStorage.getItem(DISMISS_KEY) ?? 0);
    if (dismissedAt && Date.now() - dismissedAt < DISMISS_TTL_MS) return;

    const onPrompt = (e: Event) => {
      e.preventDefault();
      setDeferred(e as DeferredPrompt);
      setOpen(true);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);

    // iOS fallback: nudge after a short delay so it doesn't fight first paint
    if (isIOS()) {
      const t = window.setTimeout(() => {
        setShowIOS(true);
        setOpen(true);
      }, 4000);
      return () => {
        window.removeEventListener("beforeinstallprompt", onPrompt);
        window.clearTimeout(t);
      };
    }

    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
    setOpen(false);
  };

  const install = async () => {
    if (!deferred) return;
    await deferred.prompt();
    const { outcome } = await deferred.userChoice;
    if (outcome === "accepted") {
      setOpen(false);
    } else {
      dismiss();
    }
    setDeferred(null);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-x-3 bottom-3 z-50 sm:bottom-4 sm:left-auto sm:right-4 sm:w-[360px]">
      <div className="rounded-2xl border bg-card p-4 shadow-[var(--shadow-pop)]">
        <div className="flex items-start gap-3">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground">
            <Download className="h-5 w-5" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold">Install Spark</h3>
            {showIOS ? (
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                Tap <Share className="inline h-3 w-3 -translate-y-px" /> Share, then{" "}
                <span className="font-medium text-foreground">Add to Home Screen</span> for the full app experience.
              </p>
            ) : (
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                Get one-tap access, offline support, and push-style notifications for live offers near you.
              </p>
            )}
            {!showIOS && (
              <div className="mt-3 flex gap-2">
                <Button size="sm" onClick={install}>Install</Button>
                <Button size="sm" variant="ghost" onClick={dismiss}>Not now</Button>
              </div>
            )}
          </div>
          <button
            onClick={dismiss}
            aria-label="Dismiss install prompt"
            className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
