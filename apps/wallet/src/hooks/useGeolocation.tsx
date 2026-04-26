import { useCallback, useEffect, useRef, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "sonner";
import { nearestSupportedCity, normaliseCity, reverseGeocodeCity } from "@/lib/geo";

export type GeoStatus =
  | "unsupported"
  | "idle"        // not yet asked
  | "prompting"   // request in flight
  | "granted"     // we have a fix
  | "denied"
  | "error";

export interface Coords { lat: number; lng: number; accuracy?: number; ts: number }

const STORAGE_KEY = "spark.geo.coords";
const CITY_KEY = "spark.geo.city";
const DISMISS_KEY = "spark.geo.dismissed";
const STALE_MS = 1000 * 60 * 30; // 30 min

const readCached = (): Coords | null => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const c = JSON.parse(raw) as Coords;
    if (Date.now() - c.ts > STALE_MS) return null;
    return c;
  } catch { return null; }
};

const readCachedCity = (): { name: string; supported: string } | null => {
  try {
    const raw = localStorage.getItem(CITY_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
};

export const useGeolocation = () => {
  const { user } = useAuth();
  const supported = typeof navigator !== "undefined" && "geolocation" in navigator;

  const [status, setStatus] = useState<GeoStatus>(() => {
    if (!supported) return "unsupported";
    return readCached() ? "granted" : "idle";
  });
  const [coords, setCoords] = useState<Coords | null>(() => readCached());
  const [error, setError] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState<boolean>(
    () => typeof window !== "undefined" && localStorage.getItem(DISMISS_KEY) === "1"
  );
  // City resolved from coords. `name` is the raw locality (e.g. "Esslingen am Neckar"),
  // `supported` is the closest city we actually have data for (e.g. "Stuttgart").
  const [resolvedCity, setResolvedCity] = useState<{ name: string; supported: string } | null>(
    () => readCachedCity()
  );

  const persistedRef = useRef(false);
  const cityLookupRef = useRef<string | null>(null);

  // Sync coords + resolved city to customer_prefs once per session
  useEffect(() => {
    if (!user || !coords || persistedRef.current) return;
    persistedRef.current = true;
    const payload = {
      user_id: user.id,
      lat: coords.lat,
      lng: coords.lng,
      ...(resolvedCity?.supported ? { city: resolvedCity.supported } : {}),
    };
    supabase.from("customer_prefs")
      .upsert(payload)
      .then(({ error }) => { if (error) console.warn("geo sync failed", error.message); });
  }, [user, coords, resolvedCity]);

  // Reverse-geocode whenever we get a fresh fix (and haven't already resolved this point).
  useEffect(() => {
    if (!coords) return;
    const key = `${coords.lat.toFixed(3)},${coords.lng.toFixed(3)}`;
    if (cityLookupRef.current === key) return;
    cityLookupRef.current = key;

    const ctrl = new AbortController();
    (async () => {
      const raw = await reverseGeocodeCity(coords.lat, coords.lng, ctrl.signal);
      const supportedHit = normaliseCity(raw) ?? nearestSupportedCity(coords);
      const next = { name: raw ?? supportedHit, supported: supportedHit };
      setResolvedCity(next);
      try { localStorage.setItem(CITY_KEY, JSON.stringify(next)); } catch {}
    })();
    return () => ctrl.abort();
  }, [coords]);

  // Probe permission state without prompting (where supported)
  useEffect(() => {
    if (!supported) return;
    const perms = (navigator as any).permissions;
    if (!perms?.query) return;
    perms.query({ name: "geolocation" as PermissionName }).then((p: PermissionStatus) => {
      if (p.state === "denied") setStatus((s) => (s === "granted" ? s : "denied"));
      p.onchange = () => {
        if (p.state === "denied") setStatus("denied");
        if (p.state === "granted" && !coords) request();
      };
    }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [supported]);

  const request = useCallback((): Promise<Coords | null> => {
    if (!supported) return Promise.resolve(null);
    setStatus("prompting");
    setError(null);
    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const c: Coords = {
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
            ts: Date.now(),
          };
          localStorage.setItem(STORAGE_KEY, JSON.stringify(c));
          setCoords(c);
          setStatus("granted");
          toast.success("Location on — sorting offers by walk time.");
          resolve(c);
        },
        (err) => {
          if (err.code === err.PERMISSION_DENIED) {
            setStatus("denied");
            setError("Permission denied");
          } else {
            setStatus("error");
            setError(err.message || "Couldn't read location");
            toast.error("Couldn't read your location — using city centre as a fallback.");
          }
          resolve(null);
        },
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 5 * 60 * 1000 }
      );
    });
  }, [supported]);

  const dismiss = useCallback(() => {
    localStorage.setItem(DISMISS_KEY, "1");
    setDismissed(true);
  }, []);

  const clear = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(CITY_KEY);
    setCoords(null);
    setResolvedCity(null);
    cityLookupRef.current = null;
    setStatus(supported ? "idle" : "unsupported");
  }, [supported]);

  return { status, coords, error, dismissed, request, dismiss, clear, supported, resolvedCity };
};
