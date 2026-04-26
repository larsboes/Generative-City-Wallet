import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Sun, Cloud, CloudRain, MapPin, Clock, Flame, ChevronDown, BellOff, Bell, X, Navigation, LocateFixed, Lock } from "lucide-react";
import {
  Popover, PopoverContent, PopoverTrigger,
} from "@/components/ui/popover";
import { usePushPermission } from "@/hooks/usePushPermission";
import { useGeolocation } from "@/hooks/useGeolocation";
import { CITY_CENTROIDS, walkingMinutes } from "@/lib/geo";

interface Venue {
  id: string;
  name: string;
  category: string | null;
  address: string | null;
  city: string | null;
  photo_url: string | null;
  rating: number | null;
  latitude: number | null;
  longitude: number | null;
}

interface Offer {
  id: string;
  business_id: string;
  title: string;
  description: string;
  discount_label: string | null;
  start_time: string | null;
  end_time: string | null;
  reasoning: string | null;
  goal: string | null;
  launched_at: string | null;
  is_locked?: boolean;
  unlock_threshold?: number | null;
  business?: Venue;
  walk_min?: number;
}

const CITIES = ["Stuttgart", "Berlin", "Köln"];

const MAX_WALK_OPTIONS = [10, 20, 45, 0]; // 0 = no limit

const Now = () => {
  const { user } = useAuth();
  const push = usePushPermission();
  const geo = useGeolocation();
  const [city, setCity] = useState<string>("Stuttgart");
  const [offers, setOffers] = useState<Offer[]>([]);
  const [loading, setLoading] = useState(true);
  const [maxWalk, setMaxWalk] = useState<number>(0); // minutes; 0 = any
  const [pushDismissed, setPushDismissed] = useState<boolean>(
    () => typeof window !== "undefined" && localStorage.getItem("spark.push.dismissed") === "1"
  );

  const dismissPush = () => {
    localStorage.setItem("spark.push.dismissed", "1");
    setPushDismissed(true);
  };

  // Load preferred city
  const cityManuallySetRef = useRef(false);
  useEffect(() => {
    if (!user) return;
    supabase.from("customer_prefs").select("city").eq("user_id", user.id).maybeSingle()
      .then(({ data }) => { if (data?.city) setCity(data.city); });
  }, [user]);

  // Auto-adopt the *exact* city derived from the user's coordinates
  // (unless they explicitly picked one this session).
  useEffect(() => {
    if (cityManuallySetRef.current) return;
    const exact = geo.resolvedCity?.name;
    if (exact && exact !== city) {
      setCity(exact);
    }
  }, [geo.resolvedCity, city]);

  // Resolve the "from" point for walking-time calc
  const origin = useMemo(
    () => geo.coords ?? CITY_CENTROIDS[city] ?? CITY_CENTROIDS.Stuttgart,
    [geo.coords, city]
  );
  const usingPreciseLocation = !!geo.coords;

  // Live ticking clock — drives countdowns + the time-of-day greeting.
  // 5s is enough granularity for "ends in 12m" without burning battery.
  const [tick, setTick] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setTick(Date.now()), 5000);
    return () => window.clearInterval(id);
  }, []);

  const [refreshedAt, setRefreshedAt] = useState<number>(0);

  // Load active offers (RLS allows authenticated reads on active)
  const fetchOffers = useCallback(async (signal?: { cancelled: boolean }) => {
    const { data: o } = await supabase
      .from("offers")
      .select("id, business_id, title, description, discount_label, start_time, end_time, reasoning, goal, launched_at, is_locked, unlock_threshold")
      .eq("status", "active")
      .order("launched_at", { ascending: false });

    // Exclude offers the user has already claimed (regardless of redemption state).
    let claimedOfferIds = new Set<string>();
    if (user) {
      const { data: claims } = await supabase
        .from("offer_claims")
        .select("offer_id")
        .eq("user_id", user.id);
      claimedOfferIds = new Set((claims ?? []).map((c: any) => c.offer_id));
    }

    const ids = Array.from(new Set((o ?? []).filter((x: any) => !claimedOfferIds.has(x.id)).map((x: any) => x.business_id)));
    let venuesById = new Map<string, Venue>();
    if (ids.length) {
      const { data: vs } = await supabase
        .from("businesses")
        .select("id, name, category, address, city, photo_url, rating, latitude, longitude")
        .in("id", ids);
      (vs ?? []).forEach((v: any) => venuesById.set(v.id, v));
    }
    const enriched: Offer[] = (o ?? [])
      .filter((x: any) => !claimedOfferIds.has(x.id))
      .map((x: any) => {
      const v = venuesById.get(x.business_id);
      let walk: number | undefined;
      if (v?.latitude != null && v?.longitude != null) {
        walk = walkingMinutes(origin, { lat: v.latitude, lng: v.longitude });
      } else {
        const seed = x.id.charCodeAt(0) + x.id.charCodeAt(2);
        walk = 2 + (seed % 14);
      }
      return { ...x, business: v, walk_min: walk } as Offer;
    });
    const filtered = enriched.filter((x) => !x.business?.city || x.business.city.toLowerCase().includes(city.toLowerCase()) || true);
    filtered.sort((a, b) => (a.walk_min ?? 99) - (b.walk_min ?? 99));
    if (!signal?.cancelled) {
      setOffers(filtered);
      setLoading(false);
      setRefreshedAt(Date.now());
    }
  }, [city, origin, user]);

  // Initial + city/origin changes
  useEffect(() => {
    const signal = { cancelled: false };
    setLoading(true);
    fetchOffers(signal);
    return () => { signal.cancelled = true; };
  }, [fetchOffers]);

  // Periodic background refresh (every 60s) and on tab refocus
  useEffect(() => {
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") fetchOffers();
    }, 60_000);
    const onVisible = () => {
      if (document.visibilityState === "visible") fetchOffers();
    };
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", onVisible);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", onVisible);
    };
  }, [fetchOffers]);

  // Realtime: refetch when any offer changes status / appears / disappears
  useEffect(() => {
    const channel = supabase
      .channel("wallet-offers")
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "offers" },
        () => { fetchOffers(); }
      )
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "offer_claims", filter: user ? `user_id=eq.${user.id}` : undefined },
        () => { fetchOffers(); }
      )
      .subscribe();
    return () => { supabase.removeChannel(channel); };
  }, [fetchOffers, user]);


  const updateCity = async (c: string) => {
    cityManuallySetRef.current = true;
    setCity(c);
    if (user) await supabase.from("customer_prefs").upsert({ user_id: user.id, city: c });
  };

  const now = useMemo(() => new Date(tick), [tick]);
  const hour = now.getHours();
  const greeting = useMemo(() => {
    if (hour < 10) return { eyebrow: "Morning", title: "Coffee somewhere quiet?", body: "A few cafés just opened up in your area." };
    if (hour < 12) return { eyebrow: "Late morning", title: "Brunch is calling.", body: "Pastries fresh out of the oven within walking distance." };
    if (hour >= 12 && hour < 14) return { eyebrow: "Lunchtime", title: "Hungry around 1pm?", body: "Lunch combos that fill the rooms nobody booked." };
    if (hour < 17) return { eyebrow: "Afternoon", title: "Need a slow moment?", body: "Quiet places with a fresh espresso, two minutes away." };
    if (hour < 21) return { eyebrow: "Evening", title: "Dinner without the wait.", body: "Tables free now, prices that move with demand." };
    return { eyebrow: "Late night", title: "Still up?", body: "A handful of spots still pouring." };
  }, [hour]);

  // Mock weather (deterministic per day)
  const conditions = [
    { icon: Sun, label: "Sunny", temp: 21, color: "text-amber-500" },
    { icon: Cloud, label: "Cloudy", temp: 16, color: "text-slate-500" },
    { icon: CloudRain, label: "Rainy", temp: 12, color: "text-blue-500" },
  ];
  const w = conditions[now.getDate() % conditions.length];
  const Wicon = w.icon;

  // Drop offers whose end_time has passed; re-evaluated every tick.
  const liveOffers = useMemo(
    () => offers.filter((o) => !o.end_time || minsUntil(o.end_time, tick) > 0),
    [offers, tick]
  );
  const visibleOffers = useMemo(
    () => (maxWalk > 0 ? liveOffers.filter((o) => (o.walk_min ?? 99) <= maxWalk) : liveOffers),
    [liveOffers, maxWalk]
  );
  const liveNow = visibleOffers.slice(0, 4);
  const picked = visibleOffers.slice(4);

  const refreshedSecs = refreshedAt ? Math.max(0, Math.round((tick - refreshedAt) / 1000)) : 0;

  return (
    <div>
      {/* Context strip */}
      <div className="border-b border-border/60 bg-card/40 px-5 py-3">
        <div className="flex items-center justify-between text-sm">
          <Popover>
            <PopoverTrigger asChild>
              <button className="flex items-center gap-1.5 font-medium hover:text-primary">
                <MapPin className="h-4 w-4 text-primary" />
                {city}
                <ChevronDown className="h-3 w-3 opacity-60" />
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-56 p-1" align="start">
              {/* Detected exact city — selectable */}
              {geo.resolvedCity?.name && !CITIES.includes(geo.resolvedCity.name) && (
                <button
                  onClick={() => updateCity(geo.resolvedCity!.name)}
                  className={`flex w-full items-center justify-between rounded px-2.5 py-2 text-sm hover:bg-accent ${
                    geo.resolvedCity.name === city ? "text-primary font-medium" : ""
                  }`}
                >
                  <span className="flex items-center gap-2">
                    {geo.resolvedCity.name}
                    <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide text-primary">
                      Detected
                    </span>
                  </span>
                  {geo.resolvedCity.name === city && (
                    <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                  )}
                </button>
              )}
              {CITIES.map((c) => (
                <button
                  key={c}
                  onClick={() => updateCity(c)}
                  className={`flex w-full items-center justify-between rounded px-2.5 py-2 text-sm hover:bg-accent ${
                    c === city ? "text-primary font-medium" : ""
                  }`}
                >
                  {c}
                  {c === city && <span className="h-1.5 w-1.5 rounded-full bg-primary" />}
                </button>
              ))}
            </PopoverContent>
          </Popover>

          <div className="flex items-center gap-3 text-muted-foreground">
            {geo.status === "granted" ? (
              <span
                className="flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary"
                title="Sorting by your real walking time"
              >
                <LocateFixed className="h-3 w-3" /> Precise
              </span>
            ) : geo.supported && geo.status !== "denied" ? (
              <button
                onClick={() => geo.request()}
                disabled={geo.status === "prompting"}
                className="flex items-center gap-1 rounded-full border border-border/60 px-2 py-0.5 text-[10px] font-medium hover:border-primary hover:text-primary disabled:opacity-60"
              >
                <Navigation className="h-3 w-3" />
                {geo.status === "prompting" ? "Locating…" : "Use my location"}
              </button>
            ) : null}
            <span className="font-mono text-xs">
              {String(now.getHours()).padStart(2, "0")}:{String(now.getMinutes()).padStart(2, "0")}
            </span>
            <span className="flex items-center gap-1.5 text-xs">
              <Wicon className={`h-4 w-4 ${w.color}`} />
              {w.temp}°
            </span>
          </div>
        </div>
      </div>

      {/* Greeting */}
      <section className="px-5 pb-2 pt-7">
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">{greeting.eyebrow}</p>
        <h1 className="mt-2 font-display text-3xl font-semibold leading-tight text-balance">
          {greeting.title}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">{greeting.body}</p>
      </section>

      {/* Push opt-in banner */}
      {push.supported && push.status === "default" && !pushDismissed && (
        <section className="mx-5 mt-5">
          <div className="relative flex items-start gap-3 rounded-2xl border border-primary/30 bg-primary/5 p-4">
            <button
              onClick={dismissPush}
              aria-label="Dismiss"
              className="absolute right-2 top-2 rounded-md p-1 text-muted-foreground hover:bg-background/60"
            >
              <X className="h-3.5 w-3.5" />
            </button>
            <div className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-full bg-background">
              <Bell className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0 flex-1 pr-4">
              <p className="font-display text-sm font-semibold">Catch offers as they drop</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Spark will whisper — never spam — when a nearby café opens something for you.
              </p>
              <Button size="sm" className="mt-3" onClick={() => push.request()}>
                Allow notifications
              </Button>
            </div>
          </div>
        </section>
      )}

      {/* Location opt-in banner */}
      {geo.supported && (geo.status === "idle" || geo.status === "denied") && !geo.dismissed && (
        <section className="mx-5 mt-5">
          <div className="relative flex items-start gap-3 rounded-2xl border border-border bg-card p-4">
            <button
              onClick={geo.dismiss}
              aria-label="Dismiss"
              className="absolute right-2 top-2 rounded-md p-1 text-muted-foreground hover:bg-background/60"
            >
              <X className="h-3.5 w-3.5" />
            </button>
            <div className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-full bg-primary/10">
              <Navigation className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0 flex-1 pr-4">
              <p className="font-display text-sm font-semibold">
                {geo.status === "denied" ? "Location is blocked" : "Sort by walking time"}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {geo.status === "denied"
                  ? `Allow location for this site to see real walk times. Right now we're using ${city}'s centre as a guess.`
                  : "Share your location once to see how many minutes each offer is from where you stand. Used only on this device."}
              </p>
              {geo.status === "idle" && (
                <Button size="sm" className="mt-3" onClick={() => geo.request()}>
                  <Navigation className="h-3.5 w-3.5" /> Use my location
                </Button>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Walking-time filter chips */}
      {!loading && offers.length > 0 && (
        <section className="mt-5 px-5">
          <div className="flex items-center gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <span className="flex-shrink-0 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              Within
            </span>
            {MAX_WALK_OPTIONS.map((m) => {
              const active = maxWalk === m;
              const label = m === 0 ? "Any" : `${m} min`;
              return (
                <button
                  key={m}
                  onClick={() => setMaxWalk(m)}
                  className={`flex-shrink-0 rounded-full border px-3 py-1 text-xs transition-colors ${
                    active
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-card hover:border-primary/60"
                  }`}
                >
                  {label}
                </button>
              );
            })}
            {!usingPreciseLocation && (
              <span className="ml-2 flex-shrink-0 text-[10px] italic text-muted-foreground">
                approx · from {city} centre
              </span>
            )}
          </div>
        </section>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-4 px-5 pt-6">
          <Skeleton className="h-44" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
      )}

      {/* Empty (filter zeroed out) */}
      {!loading && offers.length > 0 && visibleOffers.length === 0 && (
        <section className="mx-5 mt-6 rounded-2xl border border-dashed bg-card p-6 text-center">
          <p className="font-display text-base font-semibold">Nothing within {maxWalk} min from here.</p>
          <p className="mx-auto mt-1.5 max-w-xs text-xs text-muted-foreground">
            Try widening your radius — there are {offers.length} live offers further out.
          </p>
          <Button variant="outline" size="sm" className="mt-3" onClick={() => setMaxWalk(0)}>
            Show any distance
          </Button>
        </section>
      )}

      {/* Empty */}
      {!loading && offers.length === 0 && (
        <section className="mx-5 mt-8 rounded-2xl border border-dashed bg-card p-8 text-center">
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-accent text-accent-foreground">
            <BellOff className="h-5 w-5" />
          </div>
          <h2 className="mt-4 font-display text-xl font-semibold">No live offers in {city} yet</h2>
          <p className="mx-auto mt-2 max-w-xs text-sm text-muted-foreground">
            Spark is still warming up here. We'll buzz you the moment a nearby café drops a deal.
          </p>
          <Button asChild variant="outline" className="mt-5">
            <Link to="/wallet/me">Notification settings</Link>
          </Button>
        </section>
      )}

      {/* Live now rail */}
      {!loading && liveNow.length > 0 && (
        <section className="mt-8">
          <div className="flex items-baseline justify-between px-5">
            <h2 className="flex items-center gap-2 font-display text-xl font-semibold">
              <Flame className="h-4 w-4 text-primary" />
              Right now near you
            </h2>
            <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
              {liveNow.length} live · updated {refreshedSecs < 5 ? "now" : `${refreshedSecs}s ago`}
            </span>
          </div>
          <div className="mt-3 flex snap-x snap-mandatory gap-3 overflow-x-auto px-5 pb-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {liveNow.map((o) => (
              <FeaturedOfferCard key={o.id} offer={o} nowMs={tick} />
            ))}
          </div>
        </section>
      )}

      {/* Picked for you */}
      {!loading && picked.length > 0 && (
        <section className="mt-10 px-5">
          <h2 className="font-display text-xl font-semibold">Picked for you</h2>
          <div className="mt-3 space-y-3">
            {picked.map((o) => (
              <RowOfferCard key={o.id} offer={o} nowMs={tick} />
            ))}
          </div>
        </section>
      )}

      <div className="px-5 pt-12 pb-6 text-center text-[11px] text-muted-foreground">
        That's everything live in {city} — Spark is always listening for the next one.
      </div>
    </div>
  );
};

const FeaturedOfferCard = ({ offer, nowMs }: { offer: Offer; nowMs: number }) => {
  const countdown = offer.end_time ? formatCountdown(offer.end_time, nowMs) : null;
  const expiringSoon = offer.end_time ? minsUntil(offer.end_time, nowMs) <= 15 : false;
  return (
    <Link
      to={`/wallet/offer/${offer.id}`}
      className="group relative w-72 shrink-0 snap-start overflow-hidden rounded-2xl border bg-card shadow-[var(--shadow-card)] transition-transform active:scale-[0.99]"
    >
      <div className="relative h-40 w-full overflow-hidden bg-muted">
        {offer.business?.photo_url ? (
          <img src={offer.business.photo_url} alt={offer.business.name} className="h-full w-full object-cover transition-transform group-hover:scale-105" />
        ) : (
          <div className="grid h-full w-full place-items-center bg-gradient-to-br from-accent to-muted text-accent-foreground">
            <MapPin className="h-8 w-8" />
          </div>
        )}
        <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/80 to-transparent" />
        <div
          className={`absolute left-3 top-3 flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-primary-foreground ${
            offer.is_locked ? "bg-foreground" : expiringSoon ? "bg-destructive" : "bg-primary"
          }`}
        >
          {offer.is_locked ? (
            <><Lock className="h-3 w-3" /> Spark · {offer.unlock_threshold ?? 4} to unlock</>
          ) : (
            <><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-white" /> Live{countdown ? ` · ends in ${countdown}` : ""}</>
          )}
        </div>
        <div className="absolute right-3 top-3 rounded-full bg-white/95 px-2.5 py-1 text-[10px] font-semibold text-foreground">
          {offer.walk_min} min walk
        </div>
        <div className="absolute inset-x-3 bottom-3 text-white">
          <p className="text-[11px] uppercase tracking-wider opacity-80">{offer.business?.name}</p>
          <p className="mt-0.5 line-clamp-2 font-display text-lg font-semibold leading-tight">{offer.title}</p>
        </div>
      </div>
      {offer.discount_label && (
        <div className="border-t bg-card px-4 py-2.5 text-xs">
          <span className="font-semibold text-primary">{offer.is_locked ? "🔒 " : ""}{offer.discount_label}</span>
        </div>
      )}
    </Link>
  );
};

const RowOfferCard = ({ offer, nowMs }: { offer: Offer; nowMs: number }) => {
  const countdown = offer.end_time ? formatCountdown(offer.end_time, nowMs) : null;
  const expiringSoon = offer.end_time ? minsUntil(offer.end_time, nowMs) <= 15 : false;
  return (
    <Link
      to={`/wallet/offer/${offer.id}`}
      className="flex gap-3 rounded-xl border bg-card p-3 shadow-sm transition-shadow hover:shadow-[var(--shadow-card)] active:scale-[0.99]"
    >
      <div className="h-20 w-20 shrink-0 overflow-hidden rounded-lg bg-muted">
        {offer.business?.photo_url ? (
          <img src={offer.business.photo_url} alt="" className="h-full w-full object-cover" />
        ) : (
          <div className="grid h-full w-full place-items-center text-muted-foreground"><MapPin className="h-5 w-5" /></div>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          {offer.is_locked ? (
            <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-foreground">
              <Lock className="h-3 w-3" /> Spark · needs {offer.unlock_threshold ?? 4}
            </span>
          ) : (
            <span className={`text-[10px] font-semibold uppercase tracking-wider ${expiringSoon ? "text-destructive" : "text-primary"}`}>
              {countdown ? `Ends in ${countdown}` : "Live"}
            </span>
          )}
          <span className="text-[10px] text-muted-foreground">· {offer.walk_min} min walk</span>
        </div>
        <h3 className="mt-1 line-clamp-2 font-display text-base font-semibold leading-snug">{offer.title}</h3>
        <p className="mt-0.5 truncate text-xs text-muted-foreground">{offer.business?.name}</p>
        {offer.discount_label && (
          <p className="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-primary">
            <Clock className="h-3 w-3" /> {offer.discount_label}
          </p>
        )}
      </div>
    </Link>
  );
};

function minsUntil(time: string, nowMs: number = Date.now()): number {
  const [h, m] = time.split(":").map(Number);
  const target = new Date(nowMs);
  target.setHours(h, m, 0, 0);
  const diff = Math.round((target.getTime() - nowMs) / 60000);
  return Math.max(0, diff);
}

// Friendly countdown: "1h 12m" → "12m" → "45s" → "now"
function formatCountdown(time: string, nowMs: number): string {
  const [h, m] = time.split(":").map(Number);
  const target = new Date(nowMs);
  target.setHours(h, m, 0, 0);
  const diffMs = target.getTime() - nowMs;
  if (diffMs <= 0) return "now";
  const totalSec = Math.floor(diffMs / 1000);
  if (totalSec < 60) return `${totalSec}s`;
  const totalMin = Math.floor(totalSec / 60);
  if (totalMin < 60) return `${totalMin}m`;
  const hh = Math.floor(totalMin / 60);
  const mm = totalMin % 60;
  return `${hh}h ${mm}m`;
}

export default Now;
