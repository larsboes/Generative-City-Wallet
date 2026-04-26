import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, MapPin, Lock, Sparkles, Users, Clock } from "lucide-react";
import SparkProgressCard, { type SparkGroupState } from "@/components/SparkProgressCard";
import { formatRemaining } from "@/lib/spark";
import { toast } from "sonner";

interface OfferLite {
  id: string; title: string; description: string; discount_label: string | null;
  unlock_window_minutes: number | null; business_id: string;
}
interface Venue { id: string; name: string; photo_url: string | null; address: string | null; category: string | null; }

const SparkLanding = () => {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [joining, setJoining] = useState(false);
  const [group, setGroup] = useState<SparkGroupState | null>(null);
  const [offer, setOffer] = useState<OfferLite | null>(null);
  const [venue, setVenue] = useState<Venue | null>(null);
  const [tick, setTick] = useState(Date.now());

  useEffect(() => {
    const id = window.setInterval(() => setTick(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (!code) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      const { data, error } = await supabase.functions.invoke("spark-group", {
        body: { action: "status", share_code: code },
      });
      if (cancelled) return;
      if (error || (data as any)?.error) {
        setLoading(false);
        return;
      }
      setGroup(data as SparkGroupState);

      const { data: o } = await supabase
        .from("offers")
        .select("id, title, description, discount_label, unlock_window_minutes, business_id")
        .eq("id", (data as any).offer_id).maybeSingle();
      if (o) {
        setOffer(o as OfferLite);
        const { data: v } = await supabase
          .from("businesses").select("id, name, photo_url, address, category")
          .eq("id", (o as any).business_id).maybeSingle();
        if (!cancelled) setVenue(v as Venue);
      }
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, [code]);

  const join = async () => {
    if (!code) return;
    setJoining(true);
    const { data, error } = await supabase.functions.invoke("spark-group", {
      body: { action: "join", share_code: code },
    });
    setJoining(false);
    if (error || (data as any)?.error) {
      toast.error((data as any)?.error ?? error?.message ?? "Could not join");
      return;
    }
    setGroup(data as SparkGroupState);
    toast.success("You're in the Spark");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <div className="mx-auto max-w-md p-5">
          <Skeleton className="h-56 w-full" />
          <Skeleton className="mt-4 h-8 w-2/3" />
          <Skeleton className="mt-2 h-4 w-full" />
        </div>
      </div>
    );
  }

  if (!group || !offer) {
    return (
      <div className="grid min-h-screen place-items-center bg-background p-6 text-center">
        <div>
          <p className="font-display text-2xl font-semibold">Spark not found</p>
          <p className="mt-2 text-sm text-muted-foreground">This invite may have expired or been pulled.</p>
          <Button asChild variant="outline" className="mt-6"><Link to="/wallet">Back to Now</Link></Button>
        </div>
      </div>
    );
  }

  const isMember = !!group.claim_code;
  const expired = !group.unlocked_at && new Date(group.expires_at).getTime() < tick;

  return (
    <div className="min-h-screen bg-background grain">
      <div className="mx-auto min-h-screen max-w-md bg-background pb-24 md:max-w-lg md:border-x">
        <div className="relative h-56 overflow-hidden">
          {venue?.photo_url ? (
            <img src={venue.photo_url} alt={venue.name} className="h-full w-full object-cover" />
          ) : (
            <div className="grid h-full w-full place-items-center bg-gradient-to-br from-accent to-muted text-muted-foreground">
              <MapPin className="h-10 w-10" />
            </div>
          )}
          <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-transparent to-black/40" />
          <button
            onClick={() => navigate("/wallet")}
            className="absolute left-4 top-4 grid h-9 w-9 place-items-center rounded-full bg-white/95 text-foreground shadow-md backdrop-blur"
            aria-label="Back"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div className="absolute inset-x-4 bottom-4 flex items-center gap-2">
            <span className="flex items-center gap-1.5 rounded-full bg-primary px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-primary-foreground">
              <Lock className="h-3 w-3" /> Spark
            </span>
            {offer.discount_label && (
              <span className="rounded-full bg-white/95 px-3 py-1 text-[10px] font-semibold text-foreground">
                {offer.discount_label}
              </span>
            )}
          </div>
        </div>

        <div className="px-5 pt-6">
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">{venue?.category ?? "A friend dropped a Spark"}</p>
          <h1 className="mt-2 font-display text-3xl font-semibold leading-tight text-balance">{offer.title}</h1>
          <p className="mt-3 text-base text-muted-foreground">{offer.description}</p>

          {isMember ? (
            <div className="mt-7">
              <SparkProgressCard
                state={group}
                venueName={venue?.name}
                discountLabel={offer.discount_label}
                windowMin={offer.unlock_window_minutes ?? 30}
                onChange={setGroup}
              />
              <Button asChild variant="outline" className="mt-3 w-full">
                <Link to={`/wallet/offer/${offer.id}`}>Open offer details</Link>
              </Button>
            </div>
          ) : (
            <Card className="mt-7 overflow-hidden bg-ink p-6 text-ink-foreground shadow-[var(--shadow-pop)]">
              <p className="font-mono text-[10px] uppercase tracking-widest text-ink-foreground/50">You've been invited</p>
              <p className="mt-2 font-display text-xl font-semibold leading-tight">
                Tap in. {Math.max(0, group.threshold - group.count)} more after you and you all unlock it.
              </p>
              <div className="mt-4 flex items-center justify-between text-xs text-ink-foreground/70">
                <span className="flex items-center gap-1.5"><Users className="h-3.5 w-3.5" /> {group.count} / {group.threshold} so far</span>
                <span className="flex items-center gap-1.5"><Clock className="h-3.5 w-3.5" /> {formatRemaining(group.expires_at, tick)} left</span>
              </div>
              <Button
                onClick={join}
                disabled={joining || expired}
                className="mt-5 h-12 w-full bg-primary text-base hover:bg-primary/90"
              >
                <Sparkles className="h-4 w-4" />
                {expired ? "This Spark expired" : joining ? "Joining…" : "Join the Spark"}
              </Button>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default SparkLanding;
