import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Card } from "@/components/ui/card";
import { Bookmark, CheckCircle2, MapPin } from "lucide-react";

interface OfferRow {
  id: string;
  title: string;
  description: string;
  discount_label: string | null;
  end_time: string | null;
  business_id: string;
  business?: { name: string; photo_url: string | null; category: string | null };
  code?: string;
  redeemed_at?: string | null;
}

const Saved = () => {
  const { user } = useAuth();
  const [claimed, setClaimed] = useState<OfferRow[]>([]);
  const [bookmarked, setBookmarked] = useState<OfferRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      const [{ data: cl }, { data: bm }] = await Promise.all([
        supabase.from("offer_claims").select("offer_id, code, redeemed_at, claimed_at").eq("user_id", user.id).order("claimed_at", { ascending: false }),
        supabase.from("offer_bookmarks").select("offer_id, created_at").eq("user_id", user.id).order("created_at", { ascending: false }),
      ]);
      const ids = Array.from(new Set([...(cl ?? []).map((c: any) => c.offer_id), ...(bm ?? []).map((b: any) => b.offer_id)]));
      let offersById = new Map<string, any>();
      let venuesById = new Map<string, any>();
      if (ids.length) {
        const { data: os } = await supabase.from("offers").select("id, business_id, title, description, discount_label, end_time").in("id", ids);
        (os ?? []).forEach((o: any) => offersById.set(o.id, o));
        const bizIds = Array.from(new Set((os ?? []).map((o: any) => o.business_id)));
        if (bizIds.length) {
          const { data: vs } = await supabase.from("businesses").select("id, name, photo_url, category").in("id", bizIds);
          (vs ?? []).forEach((v: any) => venuesById.set(v.id, v));
        }
      }
      const enrich = (id: string, extra: any = {}): OfferRow | null => {
        const o = offersById.get(id);
        if (!o) return null;
        return { ...o, ...extra, business: venuesById.get(o.business_id) };
      };
      if (cancelled) return;
      setClaimed(((cl ?? []).map((c: any) => enrich(c.offer_id, { code: c.code, redeemed_at: c.redeemed_at })).filter(Boolean) as OfferRow[]));
      setBookmarked(((bm ?? []).map((b: any) => enrich(b.offer_id)).filter(Boolean) as OfferRow[]));
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, [user]);

  return (
    <div className="px-5 pt-6">
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Saved</p>
      <h1 className="mt-2 font-display text-3xl font-semibold">Your collection</h1>
      <p className="mt-2 text-sm text-muted-foreground">Codes you've claimed and offers worth a second look.</p>

      <Tabs defaultValue="claimed" className="mt-6">
        <TabsList className="grid w-full grid-cols-2 bg-muted/60">
          <TabsTrigger value="claimed">Claimed ({claimed.length})</TabsTrigger>
          <TabsTrigger value="bookmarked">Bookmarked ({bookmarked.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="claimed" className="mt-5">
          {loading ? <Skeleton className="h-32" /> :
            claimed.length === 0 ? (
              <Empty
                icon={<CheckCircle2 className="h-5 w-5" />}
                title="No codes yet"
                body="When you claim an offer, your code lives here until you redeem it."
              />
            ) : (
              <ul className="space-y-3">
                {claimed.map((o) => <ClaimedRow key={o.id} offer={o} />)}
              </ul>
            )}
        </TabsContent>

        <TabsContent value="bookmarked" className="mt-5">
          {loading ? <Skeleton className="h-32" /> :
            bookmarked.length === 0 ? (
              <Empty
                icon={<Bookmark className="h-5 w-5" />}
                title="Nothing saved"
                body="Tap the bookmark on any offer to keep it for later."
              />
            ) : (
              <ul className="space-y-3">
                {bookmarked.map((o) => <BookmarkRow key={o.id} offer={o} />)}
              </ul>
            )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

const ClaimedRow = ({ offer }: { offer: OfferRow }) => {
  const redeemed = !!offer.redeemed_at;
  return (
    <Link to={`/wallet/offer/${offer.id}`} className="block">
      <Card className={`overflow-hidden p-0 ${redeemed ? "opacity-70" : ""}`}>
        <div className="flex items-stretch">
          <div className="h-24 w-24 shrink-0 bg-muted">
            {offer.business?.photo_url ? (
              <img src={offer.business.photo_url} alt="" className="h-full w-full object-cover" />
            ) : <div className="grid h-full w-full place-items-center text-muted-foreground"><MapPin className="h-5 w-5" /></div>}
          </div>
          <div className="flex flex-1 flex-col justify-between p-3">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{offer.business?.name}</p>
              <p className="line-clamp-2 font-display text-base font-semibold leading-snug">{offer.title}</p>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span className="font-mono text-xs font-semibold tracking-widest text-primary">{offer.code}</span>
              {redeemed ? (
                <span className="flex items-center gap-1 text-[10px] text-success"><CheckCircle2 className="h-3 w-3" /> Redeemed</span>
              ) : (
                <span className="text-[10px] text-muted-foreground">Tap to show</span>
              )}
            </div>
          </div>
        </div>
      </Card>
    </Link>
  );
};

const BookmarkRow = ({ offer }: { offer: OfferRow }) => (
  <Link to={`/wallet/offer/${offer.id}`} className="flex gap-3 rounded-xl border bg-card p-3">
    <div className="h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-muted">
      {offer.business?.photo_url ? (
        <img src={offer.business.photo_url} alt="" className="h-full w-full object-cover" />
      ) : <div className="grid h-full w-full place-items-center text-muted-foreground"><MapPin className="h-4 w-4" /></div>}
    </div>
    <div className="min-w-0 flex-1">
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{offer.business?.name}</p>
      <p className="line-clamp-2 font-display text-sm font-semibold">{offer.title}</p>
      {offer.discount_label && <p className="mt-0.5 text-xs font-medium text-primary">{offer.discount_label}</p>}
    </div>
  </Link>
);

const Empty = ({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) => (
  <div className="rounded-2xl border border-dashed bg-card p-8 text-center">
    <div className="mx-auto grid h-11 w-11 place-items-center rounded-full bg-accent text-accent-foreground">{icon}</div>
    <p className="mt-4 font-display text-lg font-semibold">{title}</p>
    <p className="mx-auto mt-1 max-w-xs text-sm text-muted-foreground">{body}</p>
  </div>
);

export default Saved;
