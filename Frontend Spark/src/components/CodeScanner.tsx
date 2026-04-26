import { useCallback, useEffect, useRef, useState } from "react";
import { BrowserMultiFormatReader } from "@zxing/browser";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AlertCircle, Camera, RotateCw, ShieldAlert } from "lucide-react";

type PermissionState = "idle" | "prompting" | "granted" | "denied" | "unsupported";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCode: (code: string) => void;
}

// Pulls a 4-char alphanumeric Spark code out of any decoded payload — accepts
// "A4F2", "SPARK-A4F2", "SPARK-SPARK-A4F2" (legacy double-prefix), or wallet
// links like ".../wallet?code=SPARK-A4F2".
const extractSparkCode = (raw: string): string | null => {
  // Strip every leading "SPARK-" / "SPARK " / "SPARK_" repeat, then grab the
  // first 4 alphanumerics. This avoids the old bug where /SPARK-([A-Z0-9]{4})/
  // greedily captured "SPAR" from "SPARK-SPARK-A4F2".
  const cleaned = raw.trim().toUpperCase().replace(/(?:SPARK[-_\s]?)+/g, "");
  const tokenMatch = cleaned.match(/[A-Z0-9]{4}/);
  return tokenMatch ? tokenMatch[0] : null;
};

const CodeScanner = ({ open, onOpenChange, onCode }: Props) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const readerRef = useRef<BrowserMultiFormatReader | null>(null);
  const controlsRef = useRef<{ stop: () => void } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState<string | undefined>(undefined);
  const [permission, setPermission] = useState<PermissionState>("idle");

  // Hard stop helper — releases the camera and tears down the zxing reader.
  const stopScanner = useCallback(() => {
    try {
      controlsRef.current?.stop();
    } catch {
      /* ignore */
    }
    controlsRef.current = null;
    readerRef.current = null;
    const v = videoRef.current;
    if (v?.srcObject instanceof MediaStream) {
      v.srcObject.getTracks().forEach((t) => t.stop());
      v.srcObject = null;
    }
  }, []);

  // Reset state every time the dialog opens/closes.
  useEffect(() => {
    if (!open) {
      stopScanner();
      setError(null);
      setDeviceId(undefined);
      setDevices([]);
      setPermission("idle");
      return;
    }
    setError(null);

    // Detect missing browser API up front (http://, in-app webviews, etc).
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setPermission("unsupported");
      return;
    }

    // Check if this iframe was granted camera permission by its parent.
    // Lovable preview iframes don't get camera by default — surface a clear
    // message so users know to open the live preview in a new tab.
    if (window.self !== window.top) {
      // We can't reliably detect allow="camera" from inside, but Permissions
      // API will say "denied" or getUserMedia will throw NotAllowedError.
      // We still let them try via the button.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Start the scanner. Called directly from the user-gesture button click so
  // iOS Safari shows the native permission prompt.
  const startScanning = async (preferredDeviceId?: string) => {
    setPermission("prompting");
    setError(null);
    try {
      // 1) Acquire stream with back camera preference. This triggers the prompt.
      const constraints: MediaStreamConstraints = preferredDeviceId
        ? { video: { deviceId: { exact: preferredDeviceId } }, audio: false }
        : { video: { facingMode: { ideal: "environment" } }, audio: false };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);

      // 2) Now that labels are populated, list devices for the flip-camera control.
      const allDevices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = allDevices.filter((d) => d.kind === "videoinput");
      setDevices(videoDevices);
      const activeTrack = stream.getVideoTracks()[0];
      const activeId = activeTrack?.getSettings().deviceId ?? preferredDeviceId;
      if (activeId) setDeviceId(activeId);

      setPermission("granted");

      // 3) Wait a tick so React mounts the <video> element, then attach.
      await new Promise((r) => setTimeout(r, 50));
      const video = videoRef.current;
      if (!video) {
        stream.getTracks().forEach((t) => t.stop());
        setError("Camera view failed to mount. Please try again.");
        return;
      }
      video.srcObject = stream;
      await video.play().catch(() => {
        /* autoplay may reject silently — playsInline + muted should handle it */
      });

      // 4) Hand the live video element to zxing for continuous decoding.
      const reader = new BrowserMultiFormatReader();
      readerRef.current = reader;
      const controls = await reader.decodeFromVideoElement(video, (result) => {
        if (!result) return;
        const code = extractSparkCode(result.getText());
        if (!code) return;
        stopScanner();
        onCode(code);
        onOpenChange(false);
      });
      controlsRef.current = controls;
    } catch (e) {
      const err = e as DOMException;
      const name = err?.name;
      const msg = e instanceof Error ? e.message : "Camera unavailable";
      stopScanner();
      if (name === "NotAllowedError" || /permission|denied|notallowed/i.test(msg)) {
        setPermission("denied");
        setError(null);
      } else if (name === "NotFoundError" || name === "OverconstrainedError") {
        setPermission("denied");
        setError("No camera was found on this device.");
      } else if (name === "NotReadableError") {
        setPermission("denied");
        setError("Your camera is being used by another app. Close it and try again.");
      } else if (name === "SecurityError") {
        setPermission("denied");
        setError("Camera blocked. Open this page in your browser (not embedded) over HTTPS.");
      } else {
        setPermission("denied");
        setError(msg);
      }
    }
  };

  const flipCamera = async () => {
    if (devices.length < 2) return;
    const idx = devices.findIndex((d) => d.deviceId === deviceId);
    const next = devices[(idx + 1) % devices.length];
    stopScanner();
    setDeviceId(next.deviceId);
    await startScanning(next.deviceId);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="font-display flex items-center gap-2">
            <Camera className="h-4 w-4 text-primary" /> Scan a Spark code
          </DialogTitle>
          <DialogDescription>
            Point the camera at the QR code on the customer's wallet.
          </DialogDescription>
        </DialogHeader>

        {permission === "unsupported" ? (
          <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <p>
              This browser can't access the camera. Open Spark in Safari or Chrome over HTTPS, or
              type the four-character code manually instead.
            </p>
          </div>
        ) : permission === "denied" ? (
          <div className="space-y-3">
            <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
              <div className="space-y-1">
                <p className="font-medium">Camera access is blocked.</p>
                <p className="text-destructive/80">
                  {error ??
                    "Tap the lock or camera icon in your browser's address bar, allow camera access for this site, then reload and try again."}
                </p>
                <p className="text-xs text-destructive/70">
                  If you're viewing this inside an embedded preview, open the app in its own tab —
                  iframes block camera access by default.
                </p>
              </div>
            </div>
            <Button type="button" onClick={() => startScanning()} className="w-full">
              <Camera className="h-4 w-4" /> Try again
            </Button>
          </div>
        ) : permission === "idle" ? (
          <div className="space-y-4 rounded-xl border border-border/60 bg-muted/30 p-5 text-center">
            <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-primary/10 text-primary">
              <Camera className="h-6 w-6" />
            </div>
            <div className="space-y-1">
              <p className="font-medium">Allow camera access</p>
              <p className="text-sm text-muted-foreground">
                Spark needs your camera to scan the QR code on the customer's wallet. Frames stay
                on this device — nothing is recorded or uploaded.
              </p>
            </div>
            <Button type="button" onClick={() => startScanning()} className="w-full">
              <Camera className="h-4 w-4" /> Allow camera
            </Button>
          </div>
        ) : permission === "prompting" && !videoRef.current?.srcObject ? (
          <div className="space-y-4 rounded-xl border border-border/60 bg-muted/30 p-5 text-center">
            <div className="mx-auto grid h-12 w-12 animate-pulse place-items-center rounded-full bg-primary/10 text-primary">
              <Camera className="h-6 w-6" />
            </div>
            <p className="text-sm text-muted-foreground">
              Waiting for camera permission… check your browser's prompt.
            </p>
          </div>
        ) : (
          <div className="relative overflow-hidden rounded-xl bg-black">
            <video
              ref={videoRef}
              className="aspect-square w-full object-cover"
              muted
              playsInline
              autoPlay
            />
            {/* Viewfinder overlay */}
            <div className="pointer-events-none absolute inset-0 grid place-items-center">
              <div className="h-3/5 w-3/5 rounded-2xl border-2 border-white/80 shadow-[0_0_0_9999px_rgba(0,0,0,0.45)]" />
            </div>
            <p className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-black/55 px-3 py-1 text-[11px] font-medium text-white">
              Align the QR inside the frame
            </p>
          </div>
        )}

        {error && permission !== "denied" && (
          <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <div className="flex justify-between gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={flipCamera}
            disabled={devices.length < 2 || permission !== "granted"}
          >
            <RotateCw className="h-3.5 w-3.5" /> Flip camera
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default CodeScanner;
