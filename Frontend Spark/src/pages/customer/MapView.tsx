import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import mapboxgl from "mapbox-gl";
import { MapPin, Navigation, LocateFixed, ChevronRight, Sparkles, Star } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { Skeleton } from "@/components/ui/skeleton";
import { useGeolocation } from "@/hooks/useGeolocation";
import { useAuth } from "@/hooks/useAuth";
import { CITY_CENTROIDS, walkingMinutes } from "@/lib/geo";
import { cn } from "@/lib/utils";

interface Pin {
  offerId: string;
  businessId: string;
  name: string;
  category: string | null;
  address: string | null;
  rating: number | null;
  lat: number;
  lng: number;
  title: string;
  discount_label: string | null;
  walk: number;
}

const MapView = () => {
  const { user } = useAuth();
  const geo = useGeolocation();
  
  const [searchParams, setSearchParams] = useSearchParams();
  const focusBusinessId = searchParams.get("business");
  const focusOfferId = searchParams.get("offer");

  const [city, setCity] = useState("Stuttgart");
  const [pins, setPins] = useState<Pin[]>([]);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState<string | null>(null);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<Map<string, mapboxgl.Marker>>(new Map());
  const meMarkerRef = useRef<mapboxgl.Marker | null>(null);
  const cardsRef = useRef<Map<string, HTMLAnchorElement | null>>(new Map());
  const fittedRef = useRef(false);
  const focusedKeyRef = useRef<string | null>(null);

  // Token (cached in sessionStorage; auto-retries on transient 503)
  useEffect(() => {
    let cancelled = false;
    const cached = typeof window !== "undefined" ? sessionStorage.getItem("mapbox_token") : null;
    if (cached) { setToken(cached); return; }

    const load = async (attempt = 0): Promise<void> => {
      const { data, error } = await supabase.functions.invoke("get-mapbox-token");
      if (cancelled) return;
      if (!error && data?.token) {
        try { sessionStorage.setItem("mapbox_token", data.token); } catch { /* ignore */ }
        setToken(data.token);
        return;
      }
      if (attempt < 2) {
        await new Promise((r) => setTimeout(r, 600 * (attempt + 1)));
        if (!cancelled) return load(attempt + 1);
      }
      setTokenError(error?.message ?? "Could not load map");
    };
    load();
    return () => { cancelled = true; };
  }, []);


  // Persisted city as initial fallback
  useEffect(() => {
    if (!user) return;
    supabase.from("customer_prefs").select("city").eq("user_id", user.id).maybeSingle()
      .then(({ data }) => {
        if (data?.city && !geo.resolvedCity) setCity(data.city);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  // Prefer real locality from coords
  useEffect(() => {
    const exact = geo.resolvedCity?.name;
    if (exact && exact !== city) setCity(exact);
  }, [geo.resolvedCity]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-request location once
  useEffect(() => {
    if (geo.supported && geo.status === "idle" && !geo.dismissed) geo.request();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const origin = useMemo(
    () => geo.coords ?? CITY_CENTROIDS[city] ?? CITY_CENTROIDS.Stuttgart,
    [geo.coords, city],
  );

  // Fetch active offers + venues
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      const { data: offers } = await supabase
        .from("offers")
        .select("id, business_id, title, discount_label")
        .eq("status", "active");

      const ids = Array.from(new Set((offers ?? []).map((o) => o.business_id)));
      const venues = new Map<string, any>();
      if (ids.length) {
        const { data: vs } = await supabase
          .from("businesses")
          .select("id, name, category, address, rating, latitude, longitude")
          .in("id", ids);
        (vs ?? []).forEach((v) => venues.set(v.id, v));
      }

      const built: Pin[] = (offers ?? [])
        .map((o) => {
          const v = venues.get(o.business_id);
          if (!v || v.latitude == null || v.longitude == null) return null;
          const lat = Number(v.latitude);
          const lng = Number(v.longitude);
          return {
            offerId: o.id,
            businessId: v.id,
            name: v.name,
            category: v.category,
            address: v.address,
            rating: v.rating,
            lat,
            lng,
            title: o.title,
            discount_label: o.discount_label,
            walk: walkingMinutes(origin, { lat, lng }),
          } as Pin;
        })
        .filter((p): p is Pin => p !== null)
        .sort((a, b) => a.walk - b.walk);

      if (!cancelled) {
        setPins(built);
        setLoading(false);
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [city, origin.lat, origin.lng]);

  // Initialise map
  useEffect(() => {
    if (!token || !containerRef.current || mapRef.current) return;
    mapboxgl.accessToken = token;
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/light-v11",
      center: [origin.lng, origin.lat],
      zoom: 13,
    });
    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "top-right");
    mapRef.current = map;
    map.on("load", () => {
      setMapReady(true);
      window.requestAnimationFrame(() => map.resize());
    });

    return () => {
      setMapReady(false);
      map.remove();
      mapRef.current = null;
      markersRef.current.clear();
      meMarkerRef.current = null;
      fittedRef.current = false;
      focusedKeyRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // Sync venue markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;

    const seen = new Set<string>();
    for (const pin of pins) {
      seen.add(pin.offerId);
      const existing = markersRef.current.get(pin.offerId);
      if (existing) {
        existing.setLngLat([pin.lng, pin.lat]);
        const el = existing.getElement();
        el.dataset.active = String(activeId === pin.offerId);
        continue;
      }
      const el = document.createElement("div");
      el.className = "spark-pin";
      el.dataset.active = String(activeId === pin.offerId);
      el.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.9 5.8a2 2 0 0 0 1.3 1.3L21 12l-5.8 1.9a2 2 0 0 0-1.3 1.3L12 21l-1.9-5.8a2 2 0 0 0-1.3-1.3L3 12l5.8-1.9a2 2 0 0 0 1.3-1.3z"/></svg>`;
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        setActiveId(pin.offerId);
        map.easeTo({ center: [pin.lng, pin.lat], zoom: Math.max(map.getZoom(), 15), duration: 500 });
        const card = cardsRef.current.get(pin.offerId);
        card?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
      });
      const marker = new mapboxgl.Marker({ element: el, anchor: "center" })
        .setLngLat([pin.lng, pin.lat])
        .addTo(map);
      markersRef.current.set(pin.offerId, marker);
    }

    for (const [id, marker] of markersRef.current) {
      if (!seen.has(id)) {
        marker.remove();
        markersRef.current.delete(id);
      }
    }
  }, [pins, mapReady, activeId]);

  // "You are here" — never overrides camera focus
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !geo.coords) return;
    const lngLat: [number, number] = [geo.coords.lng, geo.coords.lat];
    if (!meMarkerRef.current) {
      const el = document.createElement("div");
      el.className = "spark-me";
      meMarkerRef.current = new mapboxgl.Marker({ element: el }).setLngLat(lngLat).addTo(map);
    } else {
      meMarkerRef.current.setLngLat(lngLat);
    }
  }, [geo.coords, mapReady]);

  // Initial fit when we first have pins (only if no deep link)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || fittedRef.current) return;
    if (focusBusinessId || focusOfferId) return; // deep-link effect handles framing
    if (!pins.length) return;
    const bounds = new mapboxgl.LngLatBounds();
    pins.forEach((p) => bounds.extend([p.lng, p.lat]));
    if (geo.coords) bounds.extend([geo.coords.lng, geo.coords.lat]);
    map.fitBounds(bounds, { padding: { top: 64, right: 48, bottom: 48, left: 48 }, maxZoom: 15 });
    fittedRef.current = true;
  }, [pins, mapReady, geo.coords, focusBusinessId, focusOfferId]);

  // Deep link focus
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    const key = focusBusinessId ? `b:${focusBusinessId}` : focusOfferId ? `o:${focusOfferId}` : null;
    if (!key || focusedKeyRef.current === key) return;
    const target = pins.find(
      (p) =>
        (focusBusinessId && p.businessId === focusBusinessId) ||
        (focusOfferId && p.offerId === focusOfferId),
    );
    if (!target) return;
    focusedKeyRef.current = key;
    fittedRef.current = true;
    setActiveId(target.offerId);
    map.flyTo({ center: [target.lng, target.lat], zoom: 16, duration: 800, essential: true });
    window.setTimeout(() => {
      cardsRef.current.get(target.offerId)?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    }, 300);
  }, [pins, mapReady, focusBusinessId, focusOfferId]);

  const clearFocus = () => {
    if (focusBusinessId || focusOfferId) {
      const next = new URLSearchParams(searchParams);
      next.delete("business");
      next.delete("offer");
      setSearchParams(next, { replace: true });
    }
  };

  return (
    <div className="flex flex-col">
      {/* Header strip — matches Now/Saved aesthetic */}
      <div className="border-b border-border/60 bg-card/40 px-5 py-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Map
            </p>
            <p className="mt-0.5 flex items-center gap-1.5 font-display text-base font-semibold">
              <MapPin className="h-3.5 w-3.5 text-primary" />
              {city}
            </p>
          </div>
          {geo.status === "granted" ? (
            <span className="flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-1 text-[10px] font-medium text-primary">
              <LocateFixed className="h-3 w-3" /> Precise
            </span>
          ) : geo.supported && geo.status !== "denied" ? (
            <button
              onClick={() => geo.request()}
              disabled={geo.status === "prompting"}
              className="flex items-center gap-1 rounded-full border border-border/70 px-2.5 py-1 text-[10px] font-medium hover:border-primary hover:text-primary disabled:opacity-60"
            >
              <Navigation className="h-3 w-3" />
              {geo.status === "prompting" ? "Locating…" : "Locate me"}
            </button>
          ) : null}
        </div>
      </div>

      {/* Map canvas */}
      <div className="relative overflow-hidden border-b border-border/60" style={{ height: "52vh", minHeight: 360, maxHeight: 470 }}>
        {(loading || !token) && !tokenError && (
          <div className="absolute inset-0 z-30 grid place-items-center bg-background/60 backdrop-blur-sm">
            <Skeleton className="h-7 w-28" />
          </div>
        )}
        {tokenError && (
          <div className="absolute inset-x-4 top-4 z-40 rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
            Map unavailable: {tokenError}
          </div>
        )}

        <div ref={containerRef} className="absolute inset-0" onClick={() => setActiveId(null)} />

        {/* Live count chip */}
        {!loading && pins.length > 0 && (
          <div className="pointer-events-none absolute left-4 top-4 z-20 rounded-full border border-border/60 bg-background/90 px-3 py-1 text-[11px] font-medium shadow-sm backdrop-blur">
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
              {pins.length} live nearby
            </span>
          </div>
        )}

        {/* Empty state */}
        {!loading && pins.length === 0 && token && (
          <div className="pointer-events-none absolute inset-x-5 top-1/2 z-20 -translate-y-1/2 rounded-2xl border border-dashed border-border/70 bg-card/95 p-5 text-center shadow-[var(--shadow-card)] backdrop-blur">
            <Sparkles className="mx-auto h-5 w-5 text-primary" />
            <p className="mt-2 font-display text-sm font-semibold">No mapped offers in {city}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              We'll plot them here the moment a nearby venue drops one.
            </p>
          </div>
        )}
      </div>

      {/* Bottom rail — horizontal venue cards (matches editorial card style) */}
      {!loading && pins.length > 0 && (
        <div className="border-t border-border/60 bg-background/95 backdrop-blur-md">
          <div className="flex items-center justify-between px-5 pb-1.5 pt-3">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Nearest first
            </p>
            {(focusBusinessId || focusOfferId) && (
              <button
                onClick={clearFocus}
                className="text-[11px] font-medium text-muted-foreground hover:text-foreground"
              >
                Clear focus
              </button>
            )}
          </div>
          <div
            className="flex snap-x snap-mandatory gap-3 overflow-x-auto px-5 pb-4 pt-2 [&::-webkit-scrollbar]:hidden"
            style={{ scrollbarWidth: "none" }}
          >
            {pins.map((p) => {
              const active = activeId === p.offerId;
              return (
                <Link
                  key={p.offerId}
                  ref={(node) => { cardsRef.current.set(p.offerId, node); }}
                  to={`/wallet/offer/${p.offerId}`}
                  onMouseEnter={() => setActiveId(p.offerId)}
                  onClick={(e) => {
                    // Tapping an unfocused card focuses it on map first, then navigates on next tap
                    if (!active) {
                      e.preventDefault();
                      setActiveId(p.offerId);
                      const map = mapRef.current;
                      if (map) map.easeTo({ center: [p.lng, p.lat], zoom: Math.max(map.getZoom(), 15), duration: 500 });
                    }
                  }}
                  className={cn(
                    "group relative flex w-[78%] shrink-0 snap-center flex-col gap-2 rounded-2xl border bg-card p-3.5 text-left shadow-[var(--shadow-card)] transition-all sm:w-[64%]",
                    active
                      ? "border-primary/70 ring-2 ring-primary/30"
                      : "border-border/70 hover:border-primary/40",
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                        {p.category ?? "Venue"} · {p.walk} min walk
                      </p>
                      <p className="mt-1 truncate font-display text-[15px] font-semibold leading-tight">
                        {p.name}
                      </p>
                    </div>
                    {p.discount_label && (
                      <span className="shrink-0 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                        {p.discount_label}
                      </span>
                    )}
                  </div>
                  <p className="line-clamp-2 text-[13px] leading-snug text-foreground/85">
                    {p.title}
                  </p>
                  <div className="mt-auto flex items-center justify-between pt-1 text-[11px] text-muted-foreground">
                    <span className="flex items-center gap-1">
                      {p.rating != null && (
                        <>
                          <Star className="h-3 w-3 fill-amber-400 stroke-amber-400" />
                          {p.rating.toFixed(1)}
                        </>
                      )}
                    </span>
                    <span className="flex items-center gap-0.5 font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
                      View offer <ChevronRight className="h-3 w-3" />
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default MapView;
