import { useEffect, useRef, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Camera, CheckCircle2, Sparkles, Trophy, ImagePlus, AlertCircle, X } from "lucide-react";
import { toast } from "sonner";

interface RedeemedClaim {
  id: string;
  code: string;
  redeemed_at: string;
  offer: { id: string; title: string; business_id: string } | null;
  business: { id: string; name: string; category: string | null } | null;
  photoCount: number;
}

interface Badge {
  badge_key: string;
  label: string;
  description: string | null;
  awarded_at: string;
}

const MAX_PHOTOS = 3;

const RedemptionRewards = () => {
  const { user } = useAuth();
  const [points, setPoints] = useState(0);
  const [badges, setBadges] = useState<Badge[]>([]);
  const [claims, setClaims] = useState<RedeemedClaim[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    if (!user) return;
    setLoading(true);
    const [{ data: pts }, { data: bs }, { data: cs }] = await Promise.all([
      supabase.from("customer_points").select("points").eq("user_id", user.id).maybeSingle(),
      supabase.from("customer_badges").select("badge_key, label, description, awarded_at").eq("user_id", user.id).order("awarded_at", { ascending: false }),
      supabase.from("offer_claims")
        .select("id, code, redeemed_at, offer_id")
        .eq("user_id", user.id)
        .not("redeemed_at", "is", null)
        .order("redeemed_at", { ascending: false })
        .limit(8),
    ]);
    setPoints(pts?.points ?? 0);
    setBadges((bs ?? []) as Badge[]);

    const offerIds = Array.from(new Set((cs ?? []).map((c: any) => c.offer_id)));
    let offers = new Map<string, any>();
    let businesses = new Map<string, any>();
    if (offerIds.length) {
      const { data: os } = await supabase
        .from("offers")
        .select("id, title, business_id")
        .in("id", offerIds);
      (os ?? []).forEach((o: any) => offers.set(o.id, o));
      const bizIds = Array.from(new Set((os ?? []).map((o: any) => o.business_id)));
      if (bizIds.length) {
        const { data: bs2 } = await supabase
          .from("businesses")
          .select("id, name, category")
          .in("id", bizIds);
        (bs2 ?? []).forEach((b: any) => businesses.set(b.id, b));
      }
    }
    const claimIds = (cs ?? []).map((c: any) => c.id);
    let counts = new Map<string, number>();
    if (claimIds.length) {
      const { data: photos } = await supabase
        .from("redemption_photos")
        .select("claim_id")
        .in("claim_id", claimIds)
        .eq("status", "verified");
      (photos ?? []).forEach((p: any) => {
        counts.set(p.claim_id, (counts.get(p.claim_id) ?? 0) + 1);
      });
    }

    setClaims(
      (cs ?? []).map((c: any) => {
        const offer = offers.get(c.offer_id);
        return {
          id: c.id,
          code: c.code,
          redeemed_at: c.redeemed_at,
          offer: offer ? { id: offer.id, title: offer.title, business_id: offer.business_id } : null,
          business: offer ? businesses.get(offer.business_id) ?? null : null,
          photoCount: counts.get(c.id) ?? 0,
        };
      })
    );
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return <Skeleton className="h-40" />;
  }

  if (claims.length === 0 && points === 0) {
    return (
      <Card className="flex flex-col items-center gap-2 p-6 text-center">
        <Trophy className="h-7 w-7 text-primary" />
        <p className="font-display text-base font-semibold">Earn Spark Points</p>
        <p className="text-xs text-muted-foreground">
          Redeem any offer, then post a fresh photo of your meal to collect points and unlock badges.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Points & badges header */}
      <Card className="flex items-center justify-between gap-3 overflow-hidden p-0">
        <div className="flex items-center gap-3 px-5 py-4">
          <div className="grid h-11 w-11 place-items-center rounded-full bg-primary/10 text-primary">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Spark Points</p>
            <p className="font-display text-2xl font-semibold">{points}</p>
          </div>
        </div>
        {badges.length > 0 && (
          <div className="flex items-center gap-1.5 border-l border-border/60 px-4 py-4">
            <Trophy className="h-4 w-4 text-primary" />
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              {badges.length} {badges.length === 1 ? "badge" : "badges"}
            </span>
          </div>
        )}
      </Card>

      {badges.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {badges.map((b) => (
            <span
              key={b.badge_key}
              title={b.description ?? undefined}
              className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/5 px-2.5 py-1 text-[11px] font-medium text-primary"
            >
              <Trophy className="h-3 w-3" /> {b.label}
            </span>
          ))}
        </div>
      )}

      {/* Recent visits */}
      {claims.map((c) => (
        <ClaimRewardCard key={c.id} claim={c} onChanged={load} />
      ))}
    </div>
  );
};

const ClaimRewardCard = ({
  claim,
  onChanged,
}: {
  claim: RedeemedClaim;
  onChanged: () => void;
}) => {
  const { user } = useAuth();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [feedback, setFeedback] = useState<{ ok: boolean; msg: string } | null>(null);

  const within2h = Date.now() - new Date(claim.redeemed_at).getTime() < 2 * 60 * 60 * 1000;
  const remaining = MAX_PHOTOS - claim.photoCount;
  const canUpload = remaining > 0 && within2h;

  const handlePick = () => fileRef.current?.click();

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !user) return;
    if (!file.type.startsWith("image/jpeg") && !file.name.toLowerCase().endsWith(".jpg") && !file.name.toLowerCase().endsWith(".jpeg")) {
      setFeedback({ ok: false, msg: "Please upload a JPEG photo straight from your camera (EXIF required)." });
      return;
    }
    if (file.size > 12 * 1024 * 1024) {
      setFeedback({ ok: false, msg: "Photo too large (max 12 MB)." });
      return;
    }
    setUploading(true);
    setFeedback(null);
    try {
      const path = `${user.id}/${claim.id}/${Date.now()}.jpg`;
      const { error: upErr } = await supabase.storage
        .from("redemption-photos")
        .upload(path, file, { contentType: "image/jpeg", upsert: false });
      if (upErr) throw upErr;

      const { data, error } = await supabase.functions.invoke("verify-redemption-photo", {
        body: { claim_id: claim.id, storage_path: path },
      });
      if (error) throw error;
      if (data?.verified) {
        const badgeText = data.badges?.length
          ? ` + ${data.badges.map((b: any) => b.label).join(", ")}`
          : "";
        toast.success(`+${data.points_awarded} Spark Points${badgeText}`);
        setFeedback({ ok: true, msg: `Verified — +${data.points_awarded} points${badgeText}.` });
        onChanged();
      } else {
        setFeedback({
          ok: false,
          msg: data?.message ?? "We couldn't verify that photo.",
        });
      }
    } catch (err) {
      const m = err instanceof Error ? err.message : "Upload failed";
      setFeedback({ ok: false, msg: m });
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card className="overflow-hidden p-0">
      <div className="flex items-start justify-between gap-3 px-4 pt-4">
        <div className="min-w-0">
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            {claim.business?.name ?? "Visit"}
          </p>
          <p className="mt-0.5 truncate font-display text-base font-semibold">
            {claim.offer?.title ?? "Redeemed offer"}
          </p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            Redeemed {new Date(claim.redeemed_at).toLocaleString()}
          </p>
        </div>
        <span className="rounded-md bg-muted px-2 py-1 font-mono text-[10px] tracking-widest">
          {claim.code}
        </span>
      </div>

      <div className="px-4 pb-4 pt-3">
        {claim.photoCount > 0 && (
          <p className="mb-2 flex items-center gap-1 text-[11px] text-primary">
            <CheckCircle2 className="h-3 w-3" /> {claim.photoCount} verified {claim.photoCount === 1 ? "photo" : "photos"}
          </p>
        )}

        {canUpload ? (
          <>
            <Button
              size="sm"
              variant={claim.photoCount === 0 ? "default" : "outline"}
              onClick={handlePick}
              disabled={uploading}
              className="w-full"
            >
              {uploading ? (
                <>Verifying photo…</>
              ) : claim.photoCount === 0 ? (
                <><Camera className="h-3.5 w-3.5" /> Post a photo · +10 pts</>
              ) : (
                <><ImagePlus className="h-3.5 w-3.5" /> Add another · {remaining} left</>
              )}
            </Button>
            <p className="mt-2 text-[10px] text-muted-foreground">
              Camera photo, taken now. We check EXIF metadata to keep it fair.
            </p>
          </>
        ) : !within2h ? (
          <p className="text-[11px] text-muted-foreground">
            Photo window closed (must be within 2h of redemption).
          </p>
        ) : (
          <p className="text-[11px] text-muted-foreground">Maximum photos collected for this visit.</p>
        )}

        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,.jpg,.jpeg"
          capture="environment"
          className="hidden"
          onChange={handleFile}
        />

        {feedback && (
          <div
            className={`mt-3 flex items-start gap-2 rounded-lg border p-2.5 text-[11px] ${
              feedback.ok
                ? "border-primary/30 bg-primary/5 text-primary"
                : "border-destructive/30 bg-destructive/5 text-destructive"
            }`}
          >
            {feedback.ok ? (
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
            ) : (
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
            )}
            <p className="flex-1">{feedback.msg}</p>
            <button onClick={() => setFeedback(null)} className="opacity-60 hover:opacity-100">
              <X className="h-3 w-3" />
            </button>
          </div>
        )}
      </div>
    </Card>
  );
};

export default RedemptionRewards;
