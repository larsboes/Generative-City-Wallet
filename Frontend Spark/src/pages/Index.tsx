import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Sparkles, ArrowRight, CloudRain, Sun, Clock, Users, MapPin, Star } from "lucide-react";
import MockAndroidDemo from "@/components/MockAndroidDemo";

const SAMPLE_OFFERS = [
  { tag: "1–2pm slump", title: "Lunch combo €6", venue: "Café Kaiserbau · Stuttgart", icon: Clock },
  { tag: "Rain incoming", title: "Hot soup, –20%", venue: "Suppdiwupp · Karlsruhe", icon: CloudRain },
  { tag: "Lapsed regulars", title: "We miss you — espresso on us", venue: "Mókuska Caffè · München", icon: Users },
  { tag: "Heatwave", title: "Iced matcha 2-for-1", venue: "Misch Misch · Stuttgart", icon: Sun },
  { tag: "Concert nearby", title: "Pre-show small plates €12", venue: "Bar Centrale · München", icon: MapPin },
  { tag: "Tuesday lull", title: "Pasta night, half a glass free", venue: "Oxford Café · Karlsruhe", icon: Star },
];

const Index = () => {
  const [demoOpen, setDemoOpen] = useState(false);
  const tapsRef = useRef<number[]>([]);

  const handleTap = () => {
    const now = Date.now();
    const taps = tapsRef.current.filter((t) => now - t < 2500);
    // Reset if there was a long pause since the last tap
    if (taps.length && now - taps[taps.length - 1] > 700) {
      tapsRef.current = [now];
      return;
    }
    taps.push(now);
    tapsRef.current = taps;
    if (taps.length >= 5) {
      tapsRef.current = [];
      setDemoOpen(true);
    }
  };

  return (
    <div className="min-h-screen bg-background" onClickCapture={handleTap}>
      {/* Nav */}
      <header className="sticky top-0 z-50 border-b border-border/60 bg-background/80 backdrop-blur-md">
        <div className="container flex h-16 items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-primary-foreground shadow-[var(--shadow-elegant)]">
              <Sparkles className="h-4 w-4" />
            </div>
            <span className="font-display text-lg font-semibold tracking-tight">Spark</span>
          </Link>
          <nav className="hidden gap-8 text-sm text-muted-foreground md:flex">
            <a href="#how" className="transition-colors hover:text-foreground">How it works</a>
            <a href="#examples" className="transition-colors hover:text-foreground">Live offers</a>
            <a href="#partners" className="transition-colors hover:text-foreground">For merchants</a>
          </nav>
          <div className="flex items-center gap-2">
            <Button variant="ghost" asChild className="hidden sm:inline-flex"><Link to="/auth">Sign in</Link></Button>
            <Button asChild size="sm" className="shadow-[var(--shadow-elegant)] sm:size-default">
              <Link to="/auth?mode=signup&role=business">
                <span className="hidden sm:inline">Start free</span>
                <span className="sm:hidden">Get started</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden grain">
        <div className="absolute inset-0 gradient-paper" />
        <div className="container relative grid gap-12 py-14 sm:py-20 md:grid-cols-12 md:gap-16 md:py-32">
          {/* Headline */}
          <div className="md:col-span-7">
            <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground shadow-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
              Built with Sparkassen, Payone & DSV-Gruppe
            </span>
            <h1 className="mt-6 font-display text-[clamp(2.25rem,7vw,5.75rem)] font-semibold leading-[0.95] text-balance sm:mt-8">
              The right offer.
              <br />
              <span className="italic text-primary">Right now.</span>
              <br />
              Right here.
            </h1>
            <p className="mt-6 max-w-xl text-base text-muted-foreground text-balance sm:mt-8 sm:text-lg">
              Spark reads the weather, the clock and your till — then crafts a tiny offer
              that nudges someone through your door at the exact moment you have a quiet
              table.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3 sm:mt-10">
              <Button size="lg" asChild className="h-12 px-6 text-base shadow-[var(--shadow-elegant)]">
                <Link to="/auth?mode=signup&role=business">List your café <ArrowRight className="h-4 w-4" /></Link>
              </Button>
              <Button size="lg" variant="outline" asChild className="h-12 px-6 text-base">
                <a href="#examples">See it in action</a>
              </Button>
            </div>
            <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-muted-foreground sm:mt-10">
              <span className="flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-success" /> No card required</span>
              <span className="flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-success" /> 5-min setup</span>
              <span className="flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-success" /> Cancel anytime</span>
            </div>
          </div>

          {/* Hero card mock */}
          <div className="relative md:col-span-5">
            <div className="absolute -inset-8 -z-10 rounded-[2rem] bg-gradient-to-br from-primary/10 via-transparent to-primary/5 blur-2xl" />
            <div className="rounded-2xl border bg-card p-1 shadow-[var(--shadow-pop)]">
              <div className="rounded-xl bg-ink p-6 text-ink-foreground">
                <div className="flex items-center justify-between text-xs text-ink-foreground/60">
                  <span className="font-mono">SPARK · 13:42</span>
                  <span className="flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" /> Live</span>
                </div>
                <p className="mt-4 text-xs uppercase tracking-widest text-ink-foreground/50">Suggested offer</p>
                <h3 className="mt-2 font-display text-2xl font-medium leading-tight">
                  Fill your 1–2pm slump with a €6 lunch combo
                </h3>
                <p className="mt-3 text-sm text-ink-foreground/70">
                  Tuesdays average <span className="font-semibold text-ink-foreground">11 covers</span> in
                  this hour — 62% below your daily mean. Spark drafted a combo for the 320 people
                  walking past in the next 45 minutes.
                </p>
                <div className="mt-5 grid grid-cols-3 gap-3 text-center">
                  <Stat label="Reach" value="320" />
                  <Stat label="Est. covers" value="+18" />
                  <Stat label="Margin" value="71%" />
                </div>
                <div className="mt-5 flex gap-2">
                  <Button size="sm" className="flex-1 bg-primary hover:bg-primary/90">Launch</Button>
                  <Button size="sm" variant="ghost" className="text-ink-foreground hover:bg-white/10">Edit</Button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Marquee */}
        <div id="examples" className="relative border-y bg-card/50 py-6">
          <p className="container mb-4 text-xs uppercase tracking-widest text-muted-foreground">
            Offers Spark generated this morning
          </p>
          <div className="overflow-hidden">
            <div className="marquee">
              {[...SAMPLE_OFFERS, ...SAMPLE_OFFERS].map(({ tag, title, venue, icon: Icon }, i) => (
                <div key={i} className="flex w-72 shrink-0 items-start gap-3 rounded-xl border bg-background p-4 shadow-sm">
                  <div className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-accent text-accent-foreground">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-[10px] uppercase tracking-wider text-primary font-semibold">{tag}</p>
                    <p className="mt-0.5 truncate font-medium">{title}</p>
                    <p className="mt-0.5 truncate text-xs text-muted-foreground">{venue}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="container py-16 sm:py-24 md:py-32">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs uppercase tracking-widest text-primary font-semibold">How Spark works</p>
          <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-balance sm:text-4xl md:text-5xl">
            Three signals, one perfectly-timed offer.
          </h2>
        </div>
        <div className="mx-auto mt-12 grid max-w-5xl gap-px overflow-hidden rounded-2xl border bg-border sm:mt-16 md:grid-cols-3">
          {[
            {
              num: "01",
              title: "Read the moment",
              body: "Weather, time of day, foot traffic and your Payone sales pattern — refreshed every 15 minutes.",
            },
            {
              num: "02",
              title: "Draft a tiny offer",
              body: "An LLM trained on hospitality data writes the headline, picks the items and prices it for your margin.",
            },
            {
              num: "03",
              title: "Send to nearby wallets",
              body: "It surfaces in customers' city wallet only when they're within walking distance and likely to come.",
            },
          ].map((step) => (
            <div key={step.num} className="bg-card p-6 sm:p-8">
              <p className="font-mono text-sm text-primary">{step.num}</p>
              <h3 className="mt-4 font-display text-xl font-semibold sm:text-2xl">{step.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Big quote / value */}
      <section className="bg-ink text-ink-foreground grain py-16 sm:py-24 md:py-32">
        <div className="container grid gap-10 md:grid-cols-12 md:gap-12">
          <div className="md:col-span-5">
            <p className="text-xs uppercase tracking-widest text-primary font-semibold">Why merchants love it</p>
            <h2 className="mt-4 font-display text-3xl font-semibold leading-tight text-balance sm:text-4xl md:text-5xl">
              You set the goal.
              <br />
              <span className="italic text-primary-glow">Spark does the rest.</span>
            </h2>
          </div>
          <div className="grid gap-6 sm:grid-cols-2 md:col-span-7">
            {[
              { k: "Average uplift", v: "+23%", d: "covers in targeted quiet windows" },
              { k: "Setup", v: "5 min", d: "from signup to first live offer" },
              { k: "Margin protection", v: "Always", d: "Spark never drops below your floor" },
              { k: "Customer reach", v: "12,000+", d: "wallet users across pilot cities" },
            ].map((s) => (
              <div key={s.k} className="border-t border-white/10 pt-6">
                <p className="text-xs uppercase tracking-widest text-ink-foreground/50">{s.k}</p>
                <p className="mt-2 font-display text-3xl font-semibold sm:text-4xl">{s.v}</p>
                <p className="mt-1 text-sm text-ink-foreground/70">{s.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section id="partners" className="container py-16 text-center sm:py-24 md:py-32">
        <h2 className="mx-auto max-w-3xl font-display text-3xl font-semibold leading-tight text-balance sm:text-4xl md:text-6xl">
          Stop discounting. <span className="italic text-primary">Start timing.</span>
        </h2>
        <p className="mx-auto mt-5 max-w-xl text-base text-muted-foreground sm:mt-6 sm:text-lg">
          Built for cafés and restaurants who'd rather have a full house at 2pm than a half-empty one all day.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3 sm:mt-10">
          <Button size="lg" asChild className="h-12 px-6 text-base shadow-[var(--shadow-elegant)] sm:px-8">
            <Link to="/auth?mode=signup&role=business">Get started — it's free</Link>
          </Button>
          <Button size="lg" variant="ghost" asChild className="h-12 px-6 text-base">
            <Link to="/auth">I already have an account</Link>
          </Button>
        </div>
      </section>

      {demoOpen && <MockAndroidDemo onExit={() => setDemoOpen(false)} />}

      <footer className="border-t bg-card/50">
        <div className="container flex flex-col items-center justify-between gap-4 py-10 text-sm text-muted-foreground sm:flex-row">
          <div className="flex items-center gap-2">
            <div className="grid h-6 w-6 place-items-center rounded bg-primary text-primary-foreground">
              <Sparkles className="h-3 w-3" />
            </div>
            <span className="font-display font-medium text-foreground">Spark</span>
            <span>· a city wallet for local merchants</span>
          </div>
          <p className="text-xs">© {new Date().getFullYear()} · Built with Sparkassen-Finanzgruppe</p>
        </div>
      </footer>
    </div>
  );
};

const Stat = ({ label, value }: { label: string; value: string }) => (
  <div className="rounded-md border border-white/10 bg-white/5 py-2">
    <p className="font-display text-xl font-semibold">{value}</p>
    <p className="text-[10px] uppercase tracking-wider text-ink-foreground/50">{label}</p>
  </div>
);

export default Index;
