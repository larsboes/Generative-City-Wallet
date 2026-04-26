import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card } from "@/components/ui/card";
import { ArrowLeft, MapPin, Clock, Star, Bookmark, BookmarkCheck, Share2, Sparkles, CheckCircle2, Phone, Globe, LocateFixed, Lock } from "lucide-react";
import { toast } from "sonner";
import { QRCodeSVG } from "qrcode.react";
import { useGeolocation } from "@/hooks/useGeolocation";
import { CITY_CENTROIDS, walkingMinutes } from "@/lib/geo";
import SparkProgressCard, { type SparkGroupState } from "@/components/SparkProgressCard";
import {
  DEMO_BUSINESS_ID,
  DEMO_CLAIM_CODE,
  DEMO_OFFER_ID,
  DEMO_REDEEMED_EVENT,
  DEMO_REDEEMED_STORAGE_KEY,
  clearDemoClaimRedeemed,
  getDemoClaimRedeemedAt,
  syncLocalDemoClaimRedeemed,
  storeDemoClaimCode,
} from "@/lib/demoOffer";

interface Venue {
  id: string; name: string; category: string | null; address: string | null;
  city: string | null; photo_url: string | null; rating: number | null;
  phone: string | null; website: string | null;
  latitude: number | null; longitude: number | null;
}

interface Offer {
  id: string; business_id: string; title: string; description: string;
  discount_label: string | null; start_time: string | null; end_time: string | null;
  reasoning: string | null; goal: string | null; audience: string | null;
  is_locked: boolean; unlock_threshold: number | null; unlock_window_minutes: number | null;
}

const OfferDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const geo = useGeolocation();
  const [offer, setOffer] = useState<Offer | null>(null);
  const [venue, setVenue] = useState<Venue | null>(null);
  const [loading, setLoading] = useState(true);
  const [bookmarked, setBookmarked] = useState(false);
  const [claim, setClaim] = useState<{ id?: string; code: string; redeemed_at: string | null } | null>(null);
  const [claiming, setClaiming] = useState(false);
  
  const [sparkGroup, setSparkGroup] = useState<SparkGroupState | null>(null);
  const [startingSpark, setStartingSpark] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      setLoading(true);

      // Demo-only offer: only accessible right after the lock-screen mock fires.
      if (id === DEMO_OFFER_ID) {
        if (sessionStorage.getItem("spark-demo-offer") !== "1") {
          if (!cancelled) { setOffer(null); setLoading(false); }
          return;
        }
        const demoOffer: Offer = {
          id: DEMO_OFFER_ID,
          business_id: DEMO_BUSINESS_ID,
          title: "Cold drink on us — 10% off",
          description:
            "You just finished a run nearby — cool down with –10% on any cold drink at Landbäckerei IHLE. Valid for the next 60 minutes.",
          discount_label: "–10% any cold drink",
          start_time: null,
          end_time: null,
          reasoning: "Triggered after a Strava run completion within walking distance.",
          goal: "Reward post-workout customers",
          audience: "Runners nearby",
          is_locked: false,
          unlock_threshold: null,
          unlock_window_minutes: null,
        };
        const demoVenue: Venue = {
          id: DEMO_BUSINESS_ID,
          name: "Landbäckerei IHLE",
          category: "Bakery",
          address: "Balanstraße 73, 81541 München",
          city: "Munich",
          photo_url: "/venues/landbaeckerei-ihle.jpg",
          rating: 4.5,
          phone: null,
          website: null,
          latitude: 48.1142,
          longitude: 11.5998,
        };
        if (!cancelled) {
          setOffer(demoOffer);
          setVenue(demoVenue);
          setLoading(false);
        }
        return;
      }

      const { data: o } = await supabase
        .from("offers")
        .select("id, business_id, title, description, discount_label, start_time, end_time, reasoning, goal, audience, is_locked, unlock_threshold, unlock_window_minutes")
        .eq("id", id)
        .maybeSingle();
      if (!o) { if (!cancelled) { setLoading(false); } return; }
      const { data: v } = await supabase
        .from("businesses")
        .select("id, name, category, address, city, photo_url, rating, website, latitude, longitude")
        .eq("id", (o as any).business_id)
        .maybeSingle();
      if (cancelled) return;
      setOffer(o as Offer);
      setVenue(v as Venue | null);

      // Bookmark + claim state
      if (user) {
        const [{ data: bm }, { data: cl }] = await Promise.all([
          supabase.from("offer_bookmarks").select("id").eq("user_id", user.id).eq("offer_id", id).maybeSingle(),
          supabase.from("offer_claims").select("id, code, group_id, redeemed_at").eq("user_id", user.id).eq("offer_id", id).order("claimed_at", { ascending: false }).limit(1).maybeSingle(),
        ]);
        setBookmarked(!!bm);
        if (cl?.code) setClaim({ id: (cl as any).id, code: cl.code, redeemed_at: (cl as any).redeemed_at ?? null });

        // If this offer is locked and user has a claim with a group, hydrate Spark state
        if ((o as any).is_locked && cl?.group_id) {
          const { data: g } = await supabase
            .from("offer_groups").select("share_code").eq("id", cl.group_id).maybeSingle();
          if (g?.share_code) {
            const { data: status } = await supabase.functions.invoke("spark-group", {
              body: { action: "status", share_code: g.share_code },
            });
            if (status && !(status as any).error) setSparkGroup(status as SparkGroupState);
          }
        }
      }
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, [id, user]);

  // Live-update the wallet the moment the merchant marks this claim redeemed,
  // so the customer can't accidentally re-show an already-used QR.
  useEffect(() => {
    if (!user || !id) return;
    const channel = supabase
      .channel(`claim-${id}-${user.id}`)
      .on(
        "postgres_changes",
        { event: "UPDATE", schema: "public", table: "offer_claims", filter: `user_id=eq.${user.id}` },
        (payload) => {
          const row = payload.new as { offer_id: string; code: string; redeemed_at: string | null; id: string };
          if (row.offer_id !== id) return;
          setClaim((prev) => (prev ? { ...prev, id: row.id, code: row.code, redeemed_at: row.redeemed_at } : prev));
          if (row.redeemed_at) toast.success("Code redeemed at the counter");
        }
      )
      .subscribe();
    return () => { supabase.removeChannel(channel); };
  }, [id, user]);

  // Demo offer uses a shared backend row so separate customer/merchant devices
  // can sync the redemption state immediately.
  useEffect(() => {
    if (id !== DEMO_OFFER_ID) return;
    let lastAt: string | null = null;
    let toastedAt: string | null = null;
    const apply = (at: string | null, opts?: { silent?: boolean }) => {
      if (!at || at === lastAt) return;
      lastAt = at;
      setClaim((prev) => (prev ? { ...prev, redeemed_at: at } : prev));
      if (!opts?.silent && toastedAt !== at) {
        toastedAt = at;
        toast.success("Code redeemed at the counter");
      }
    };
    const onCustom = (e: Event) => {
      const at = (e as CustomEvent<{ at: string }>).detail?.at ?? new Date().toISOString();
      apply(at);
    };
    const onStorage = (e: StorageEvent) => {
      if (e.key === DEMO_REDEEMED_STORAGE_KEY && e.newValue) apply(e.newValue);
    };
    window.addEventListener(DEMO_REDEEMED_EVENT, onCustom as EventListener);
    window.addEventListener("storage", onStorage);
    // Hydrate immediately if it was redeemed before this view mounted — silently.
    apply(getDemoClaimRedeemedAt(), { silent: true });
    supabase
      .from("demo_redemptions" as any)
      .select("redeemed_at")
      .eq("code", DEMO_CLAIM_CODE)
      .maybeSingle()
      .then(({ data }) => {
        const redeemedAt = (data as { redeemed_at?: string | null } | null)?.redeemed_at;
        if (redeemedAt) {
          syncLocalDemoClaimRedeemed(redeemedAt);
          apply(redeemedAt, { silent: true });
        }
      });
    const channel = supabase
      .channel("demo-redemption-HNTN")
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "demo_redemptions", filter: `code=eq.${DEMO_CLAIM_CODE}` },
        (payload) => {
          const row = payload.new as { redeemed_at?: string | null };
          if (row.redeemed_at) {
            syncLocalDemoClaimRedeemed(row.redeemed_at);
            apply(row.redeemed_at);
          }
        }
      )
      .subscribe();
    return () => {
      window.removeEventListener(DEMO_REDEEMED_EVENT, onCustom as EventListener);
      window.removeEventListener("storage", onStorage);
      supabase.removeChannel(channel);
    };
  }, [id]);

  const startSpark = async () => {
    if (!offer) return;
    setStartingSpark(true);
    const { data, error } = await supabase.functions.invoke("spark-group", {
      body: { action: "start", offer_id: offer.id },
    });
    setStartingSpark(false);
    if (error || (data as any)?.error) {
      toast.error((data as any)?.error ?? error?.message ?? "Could not start a Spark");
      return;
    }
    setSparkGroup(data as SparkGroupState);
    if ((data as any).claim_code) setClaim({ code: (data as any).claim_code, redeemed_at: null });
    toast.success("Spark dropped — share it with your group");
  };

  const toggleBookmark = async () => {
    if (!user || !offer) return;
    if (bookmarked) {
      await supabase.from("offer_bookmarks").delete().eq("user_id", user.id).eq("offer_id", offer.id);
      setBookmarked(false);
      toast("Removed from saved");
    } else {
      const { error } = await supabase.from("offer_bookmarks").insert({ user_id: user.id, offer_id: offer.id });
      if (error) return toast.error(error.message);
      setBookmarked(true);
      toast.success("Saved for later");
    }
  };

  const claimOffer = async () => {
    if (!user || !offer) return;
    if (claim) return; // QR already visible inline; nothing to do
    setClaiming(true);
    const code = offer.id === DEMO_OFFER_ID ? DEMO_CLAIM_CODE : Math.random().toString(36).slice(2, 6).toUpperCase();
    // Demo offer has non-UUID ids; skip DB write and show a local QR only.
    if (offer.id === DEMO_OFFER_ID) {
      // Remember this code so the merchant-side scanner recognises it as a
      // demo redemption (no DB lookup, no price prompt).
      storeDemoClaimCode(code);
      // Reset any prior demo redemption flag so this fresh claim shows as live.
      clearDemoClaimRedeemed();
      supabase
        .from("demo_redemptions" as any)
        .upsert({ code: DEMO_CLAIM_CODE, redeemed_at: null } as any, { onConflict: "code" })
        .then(({ error }) => {
          if (error) console.warn("Failed to reset demo redemption", error.message);
        });
      setClaim({ code, redeemed_at: null });
      setClaiming(false);
      return;
    }
    // Store the bare 4-char token. The "SPARK-" prefix is added only when we
    // render the QR — storing it twice produced "SPARK-SPARK-XXXX" QRs that
    // confused the scanner regex.
    const { data: inserted, error } = await supabase
      .from("offer_claims")
      .insert({ user_id: user.id, offer_id: offer.id, code })
      .select("id")
      .maybeSingle();
    setClaiming(false);
    if (error) return toast.error(error.message);
    setClaim({ id: inserted?.id, code, redeemed_at: null });
  };

  const share = async () => {
    if (navigator.share && offer) {
      try {
        await navigator.share({ title: offer.title, text: offer.description, url: window.location.href });
      } catch {/* user cancelled */}
    } else {
      navigator.clipboard.writeText(window.location.href);
      toast.success("Link copied");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <div className="mx-auto max-w-md md:max-w-lg">
          <Skeleton className="h-72 w-full" />
          <div className="space-y-3 p-5">
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-32" />
          </div>
        </div>
      </div>
    );
  }

  if (!offer) {
    return (
      <div className="grid min-h-screen place-items-center bg-background p-6 text-center">
        <div>
          <p className="font-display text-2xl font-semibold">Offer no longer live</p>
          <p className="mt-2 text-sm text-muted-foreground">This deal might have ended or been pulled.</p>
          <Button asChild variant="outline" className="mt-6"><Link to="/wallet">Back to Now</Link></Button>
        </div>
      </div>
    );
  }

  const ends = offer.end_time ? formatTime(offer.end_time) : null;
  const origin =
    geo.coords ?? CITY_CENTROIDS[venue?.city ?? ""] ?? CITY_CENTROIDS.Stuttgart;
  const walk =
    venue?.latitude != null && venue?.longitude != null
      ? walkingMinutes(origin, { lat: venue.latitude, lng: venue.longitude })
      : 2 + ((offer.id.charCodeAt(0) + offer.id.charCodeAt(2)) % 14);
  const walkPrecise = !!geo.coords && venue?.latitude != null && venue?.longitude != null;

  return (
    <div className="min-h-screen bg-background grain">
      <div className="mx-auto min-h-screen max-w-md bg-background pb-24 md:max-w-lg md:border-x">
        {/* Hero */}
        <div className="relative h-72 overflow-hidden">
          {venue?.photo_url ? (
            <img src={venue.photo_url} alt={venue.name} className="h-full w-full object-cover" />
          ) : (
            <div className="grid h-full w-full place-items-center bg-gradient-to-br from-accent to-muted text-muted-foreground">
              <MapPin className="h-10 w-10" />
            </div>
          )}
          <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-transparent to-black/40" />

          {/* Top bar */}
          <div className="absolute inset-x-0 top-0 flex items-center justify-between p-4">
            <button
              onClick={() => navigate(-1)}
              className="grid h-9 w-9 place-items-center rounded-full bg-white/95 text-foreground shadow-md backdrop-blur"
              aria-label="Back"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div className="flex gap-2">
              <button
                onClick={share}
                className="grid h-9 w-9 place-items-center rounded-full bg-white/95 text-foreground shadow-md backdrop-blur"
                aria-label="Share"
              >
                <Share2 className="h-4 w-4" />
              </button>
              <button
                onClick={toggleBookmark}
                className="grid h-9 w-9 place-items-center rounded-full bg-white/95 text-foreground shadow-md backdrop-blur"
                aria-label="Save"
              >
                {bookmarked ? <BookmarkCheck className="h-4 w-4 text-primary" /> : <Bookmark className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {/* Bottom badges */}
          <div className="absolute inset-x-4 bottom-4 flex items-center gap-2">
            <span className="flex items-center gap-1.5 rounded-full bg-primary px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-primary-foreground">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-white" /> Live
            </span>
            {ends && (
              <span className="rounded-full bg-white/95 px-3 py-1 text-[10px] font-semibold text-foreground">
                Until {ends}
              </span>
            )}
            <span className="flex items-center gap-1 rounded-full bg-white/95 px-3 py-1 text-[10px] font-semibold text-foreground">
              {walkPrecise && <LocateFixed className="h-3 w-3 text-primary" />}
              {walk} min walk{!walkPrecise && venue?.latitude != null ? " · approx" : ""}
            </span>
          </div>
        </div>

        {/* Body */}
        <div className="px-5 pt-6">
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">{venue?.category ?? "Local merchant"}</p>
          <h1 className="mt-2 font-display text-3xl font-semibold leading-tight text-balance">{offer.title}</h1>
          <p className="mt-3 text-base text-muted-foreground">{offer.description}</p>

          {offer.discount_label && (
            <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-accent px-3 py-1.5 text-sm font-semibold text-primary">
              <Sparkles className="h-3.5 w-3.5" /> {offer.discount_label}
            </div>
          )}

          {offer.reasoning && (
            <div className="mt-6 rounded-xl border-l-2 border-primary/40 bg-muted/40 px-4 py-3">
              <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Why you're seeing this</p>
              <p className="mt-1.5 text-sm italic leading-relaxed">{offer.reasoning}</p>
            </div>
          )}

          {/* Claim / Spark card */}
          {offer.is_locked ? (
            sparkGroup ? (
              <div className="mt-7">
                <SparkProgressCard
                  state={sparkGroup}
                  venueName={venue?.name}
                  discountLabel={offer.discount_label}
                  windowMin={offer.unlock_window_minutes ?? 30}
                  onChange={setSparkGroup}
                />
              </div>
            ) : (
              <Card className="mt-7 overflow-hidden bg-ink p-6 text-ink-foreground shadow-[var(--shadow-pop)]">
                <div className="flex items-center gap-2 text-primary">
                  <Lock className="h-4 w-4" />
                  <p className="font-mono text-[10px] uppercase tracking-widest">Locked offer</p>
                </div>
                <p className="mt-3 font-display text-xl font-semibold leading-tight">
                  Unlock {offer.discount_label ?? "this deal"} with {Math.max(1, (offer.unlock_threshold ?? 4) - 1)} friends.
                </p>
                <p className="mt-2 text-sm text-ink-foreground/70">
                  Drop a Spark, share the link in your group chat. If {offer.unlock_threshold ?? 4} of you tap in within{" "}
                  {offer.unlock_window_minutes ?? 30} min, you all get it.
                </p>
                <Button onClick={startSpark} disabled={startingSpark} className="mt-5 h-12 w-full bg-primary text-base hover:bg-primary/90">
                  <Sparkles className="h-4 w-4" /> {startingSpark ? "Lighting it up…" : "Drop a Spark"}
                </Button>
              </Card>
            )
          ) : (
            <Card className="mt-7 overflow-hidden bg-ink p-5 text-ink-foreground shadow-[var(--shadow-pop)] sm:p-6">
              <div className="flex items-baseline justify-between">
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-widest text-ink-foreground/50">
                    {claim?.redeemed_at ? "Redeemed" : claim ? "Your code" : "Claim this offer"}
                  </p>
                  {claim ? (
                    <p className="mt-2 font-mono text-2xl font-semibold tracking-widest">
                      <span className="text-ink-foreground/50">SPARK-</span>
                      {claim.code.replace(/^SPARK[-_\s]?/i, "")}
                    </p>
                  ) : (
                    <p className="mt-2 font-display text-xl font-semibold leading-tight">
                      Show this at the counter — no signup, no fuss.
                    </p>
                  )}
                </div>
                {claim && <CheckCircle2 className={`h-7 w-7 ${claim.redeemed_at ? "text-success" : "text-success/70"}`} />}
              </div>

              {!claim ? (
                <Button onClick={claimOffer} disabled={claiming} className="mt-5 h-12 w-full bg-primary text-base hover:bg-primary/90">
                  {claiming ? "Claiming…" : "Claim offer"}
                </Button>
              ) : claim.redeemed_at ? (
                <div className="mt-5 rounded-2xl border border-ink-foreground/10 bg-ink-foreground/5 p-4 text-center sm:p-5">
                  <CheckCircle2 className="mx-auto h-10 w-10 text-success" />
                  <p className="mt-3 font-display text-lg font-semibold">All done — enjoy it</p>
                  <p className="mt-1 text-xs text-ink-foreground/60">
                    Redeemed {new Date(claim.redeemed_at).toLocaleString()}. This code can't be used again.
                  </p>
                </div>
              ) : (
                <>
                  <div className="mt-5 flex justify-center">
                    <div className="rounded-2xl bg-white p-4">
                      <QRCodeSVG
                        value={`SPARK-${claim.code.replace(/^SPARK[-_\s]?/i, "")}`}
                        size={168}
                        level="M"
                        marginSize={0}
                      />
                    </div>
                  </div>
                  <p className="mt-3 text-center text-xs text-ink-foreground/60">
                    Show this QR at the counter — the merchant scans it to redeem.
                  </p>
                </>
              )}
            </Card>
          )}

          {/* Venue */}
          {venue && (
            <section className="mt-8 mb-2">
              <h2 className="font-display text-lg font-semibold">About {venue.name}</h2>
              <Card className="mt-3 p-4">
                <div className="flex items-start gap-3">
                  {venue.photo_url ? (
                    <img src={venue.photo_url} alt="" className="h-14 w-14 shrink-0 rounded-lg object-cover" />
                  ) : (
                    <div className="grid h-14 w-14 place-items-center rounded-lg bg-muted text-muted-foreground"><MapPin className="h-5 w-5" /></div>
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{venue.name}</p>
                    {venue.category && <p className="text-xs text-muted-foreground">{venue.category}</p>}
                    {venue.rating != null && (
                      <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                        <Star className="h-3 w-3 fill-current text-primary" /> {Number(venue.rating).toFixed(1)}
                      </p>
                    )}
                  </div>
                </div>
                <dl className="mt-4 space-y-2 text-sm">
                  {venue.address && (
                    <div className="flex gap-2"><MapPin className="h-4 w-4 shrink-0 text-muted-foreground" /><span>{venue.address}</span></div>
                  )}
                  {venue.phone && (
                    <a href={`tel:${venue.phone}`} className="flex gap-2 text-foreground hover:text-primary"><Phone className="h-4 w-4 shrink-0 text-muted-foreground" />{venue.phone}</a>
                  )}
                  {venue.website && (
                    <a href={venue.website} target="_blank" rel="noopener noreferrer" className="flex gap-2 truncate text-foreground hover:text-primary">
                      <Globe className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span className="truncate">{venue.website}</span>
                    </a>
                  )}
                </dl>
              </Card>
            </section>
          )}
        </div>

      </div>
    </div>
  );
};

const formatTime = (t: string) => t.slice(0, 5);

export default OfferDetail;
