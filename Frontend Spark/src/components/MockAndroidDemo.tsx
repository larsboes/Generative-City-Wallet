import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, Signal, Wifi, BatteryFull, Phone, Camera, ChevronUp, ChevronRight, Lock } from "lucide-react";

interface Props {
  onExit: () => void;
}

const OFFER_PATH = "/wallet/offer/demo-cold-drink";

// Stylised Strava-like "S" mark — recreated with SVG so we don't ship the trademark asset.
const StravaMark = ({ className = "" }: { className?: string }) => (
  <div
    className={`grid place-items-center rounded-[10px] ${className}`}
    style={{ background: "#FC4C02" }}
    aria-label="Strava"
  >
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none">
      <path
        d="M9.5 3 4 13.2h3.3L9.5 9l2.2 4.2H15L9.5 3Z"
        fill="#fff"
      />
      <path
        d="M14.2 14.4 12.6 17.5l-1.6-3.1H8.7l3.9 6.6 3.9-6.6h-2.3Z"
        fill="#fff"
        fillOpacity=".75"
      />
    </svg>
  </div>
);

const SparkMark = ({ className = "" }: { className?: string }) => (
  <div
    className={`grid place-items-center rounded-[10px] bg-primary text-primary-foreground ${className}`}
    aria-label="Spark"
  >
    <Sparkles className="h-3.5 w-3.5" />
  </div>
);

type Phase = "lockscreen" | "tapping" | "splash";

const formatTime = (d: Date) =>
  `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;

const formatDate = (d: Date) =>
  d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });

export const MockAndroidDemo = ({ onExit }: Props) => {
  const navigate = useNavigate();
  const [now, setNow] = useState(new Date());
  const [showStrava, setShowStrava] = useState(false);
  const [showSpark, setShowSpark] = useState(false);
  const [phase, setPhase] = useState<Phase>("lockscreen");
  const sparkCardRef = useRef<HTMLDivElement | null>(null);

  // Tick the clock every 30s for realism.
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(t);
  }, []);

  // Sequence: strava in immediately → spark @ 5s → tap @ 8s → splash @ 9s → navigate @ 9.7s
  useEffect(() => {
    const timers: number[] = [];
    timers.push(window.setTimeout(() => setShowStrava(true), 350));
    timers.push(window.setTimeout(() => setShowSpark(true), 5_350));
    timers.push(window.setTimeout(() => setPhase("tapping"), 8_300));
    timers.push(window.setTimeout(() => setPhase("splash"), 9_300));
    timers.push(
      window.setTimeout(() => {
        sessionStorage.setItem("spark-demo-offer", "1");
        navigate(OFFER_PATH);
        onExit();
      }, 10_100),
    );
    return () => timers.forEach((id) => clearTimeout(id));
  }, [navigate, onExit]);

  // Esc to skip
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onExit();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onExit]);

  return (
    <div
      className="fixed inset-0 z-[100] overflow-hidden"
      style={{
        // One UI 8.1-ish wallpaper: deep indigo → teal → warm dusk
        background:
          "radial-gradient(at 20% 10%, #2b3a67 0%, transparent 55%), radial-gradient(at 80% 0%, #1f6e8c 0%, transparent 50%), radial-gradient(at 50% 100%, #3a2a4a 0%, transparent 60%), linear-gradient(180deg, #0f1733 0%, #142a3a 45%, #2a1f3a 100%)",
      }}
    >
      {/* faint grain */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.06] mix-blend-overlay"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='100%' height='100%' filter='url(%23n)' opacity='0.6'/></svg>\")",
        }}
      />

      {/* Skip control removed — Esc still exits */}

      {/* Lock screen content */}
      <div
        className={`relative z-10 mx-auto flex h-full w-full max-w-md flex-col px-5 text-white transition-all duration-700 ${
          phase === "splash" ? "scale-110 opacity-0" : "scale-100 opacity-100"
        }`}
        style={{ paddingTop: "max(env(safe-area-inset-top), 14px)" }}
      >
        {/* Status bar */}
        <div className="flex items-center justify-between text-[12px] font-medium tracking-tight">
          <span className="font-display tabular-nums">{formatTime(now)}</span>
          <div className="flex items-center gap-1.5 opacity-90">
            <Signal className="h-3 w-3" strokeWidth={2.5} />
            <Wifi className="h-3 w-3" strokeWidth={2.5} />
            <BatteryFull className="h-3.5 w-3.5" strokeWidth={2.5} />
          </div>
        </div>

        {/* Clock + date */}
        <div className="mt-7 flex flex-col items-center text-center">
          <div className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-white/70">
            <Lock className="h-3 w-3" />
            Locked
          </div>
          <div className="mt-2 font-display text-[88px] font-extralight leading-none tabular-nums tracking-tight">
            {formatTime(now)}
          </div>
          <div className="mt-2 text-[13px] font-medium text-white/85">
            {formatDate(now)} · Munich
          </div>
        </div>

        {/* Notifications stack */}
        <div className="mt-8 flex flex-col items-stretch gap-2.5">
          {/* Spark notification (rendered first so it sits on top after stacking) */}
          <div
            ref={sparkCardRef}
            className={`relative origin-top transition-all duration-500 ${
              showSpark
                ? "translate-y-0 scale-100 opacity-100"
                : "pointer-events-none -translate-y-3 scale-95 opacity-0"
            }`}
          >
            <NotificationCard
              icon={<SparkMark className="h-6 w-6" />}
              app="Spark"
              time="now"
              title="Nice run! Cool down on us ❄️"
              body="We noticed you just finished a run nearby. Grab –10% on a cold drink at Landbäckerei IHLE — 5 min walk away."
              pressed={phase === "tapping"}
            />
            {/* Tap ripple */}
            {phase === "tapping" && (
              <div className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
                <span className="block h-3 w-3 rounded-full bg-white/90 shadow-[0_0_0_4px_rgba(255,255,255,0.35)]" />
                <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
                  <span className="block h-12 w-12 animate-ping rounded-full bg-white/40" />
                </span>
              </div>
            )}
          </div>

          {/* Strava notification */}
          <div
            className={`origin-top transition-all duration-500 ${
              showStrava
                ? "translate-y-0 scale-100 opacity-100"
                : "pointer-events-none -translate-y-3 scale-95 opacity-0"
            }`}
          >
            <NotificationCard
              icon={<StravaMark className="h-6 w-6" />}
              app="Strava"
              time={showSpark ? "5s ago" : "now"}
              title="Morning run complete 🎉"
              body={"5.2 km · 27:14 · 5'14\"/km — nice pace! Tap to view your activity."}
            />
          </div>
        </div>

        <div className="flex-1" />

        {/* Bottom shortcuts + swipe hint */}
        <div className="mb-8 flex flex-col items-center gap-5">
          <div className="flex items-center gap-1.5 text-[11px] text-white/70">
            <ChevronUp className="h-3.5 w-3.5 animate-bounce" strokeWidth={2.5} />
            Swipe up to unlock
          </div>
          <div className="flex w-full items-end justify-between px-3">
            <ShortcutButton label="Phone">
              <Phone className="h-5 w-5" />
            </ShortcutButton>
            <ShortcutButton label="Camera">
              <Camera className="h-5 w-5" />
            </ShortcutButton>
          </div>
        </div>
      </div>

      {/* Spark splash on app launch */}
      <div
        className={`absolute inset-0 z-20 grid place-items-center bg-background transition-all duration-500 ${
          phase === "splash" ? "scale-100 opacity-100" : "pointer-events-none scale-90 opacity-0"
        }`}
      >
        <div className="flex flex-col items-center gap-3">
          <div className="grid h-16 w-16 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-[var(--shadow-elegant)]">
            <Sparkles className="h-8 w-8" />
          </div>
          <span className="font-display text-2xl font-semibold tracking-tight text-foreground">
            Spark
          </span>
        </div>
      </div>
    </div>
  );
};

const NotificationCard = ({
  icon,
  app,
  time,
  title,
  body,
  pressed = false,
}: {
  icon: React.ReactNode;
  app: string;
  time: string;
  title: string;
  body: string;
  pressed?: boolean;
}) => (
  <div
    className={`rounded-3xl border border-white/15 bg-white/10 p-3.5 shadow-[0_8px_24px_-12px_rgba(0,0,0,0.45)] backdrop-blur-2xl transition-transform duration-150 ${
      pressed ? "scale-[0.97]" : "scale-100"
    }`}
  >
    <div className="flex items-center gap-2">
      {icon}
      <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-white/80">
        {app}
      </span>
      <span className="text-[11px] text-white/55">·</span>
      <span className="text-[11px] text-white/55">{time}</span>
      <ChevronRight className="ml-auto h-3.5 w-3.5 text-white/55" />
    </div>
    <p className="mt-1.5 text-[14px] font-semibold leading-snug text-white">{title}</p>
    <p className="mt-0.5 text-[13px] leading-snug text-white/80">{body}</p>
  </div>
);

const ShortcutButton = ({ children, label }: { children: React.ReactNode; label: string }) => (
  <button
    aria-label={label}
    className="grid h-12 w-12 place-items-center rounded-full border border-white/15 bg-white/10 text-white shadow-lg backdrop-blur-md transition hover:bg-white/20"
  >
    {children}
  </button>
);

export default MockAndroidDemo;
