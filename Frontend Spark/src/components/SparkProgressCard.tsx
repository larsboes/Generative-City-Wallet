import { useEffect, useMemo, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Lock, Unlock, Share2, Sparkles, Clock, Users, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { buildShareText, buildShareUrl, formatRemaining } from "@/lib/spark";

export interface SparkGroupState {
  group_id: string;
  share_code: string;
  threshold: number;
  expires_at: string;
  unlocked_at: string | null;
  count: number;
  claim_code?: string | null;
}

interface Props {
  state: SparkGroupState;
  venueName?: string | null;
  discountLabel?: string | null;
  windowMin: number;
  onChange?: (next: SparkGroupState) => void;
}

const SparkProgressCard = ({ state, venueName, discountLabel, windowMin, onChange }: Props) => {
  const [tick, setTick] = useState(() => Date.now());

  useEffect(() => {
    const id = window.setInterval(() => setTick(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  // Realtime: listen for new joiners on this group
  useEffect(() => {
    const channel = supabase
      .channel(`spark-${state.group_id}`)
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "offer_claims", filter: `group_id=eq.${state.group_id}` },
        async () => {
          // Re-fetch authoritative status via edge function
          const { data } = await supabase.functions.invoke("spark-group", {
            body: { action: "status", share_code: state.share_code },
          });
          if (data && !data.error) onChange?.({ ...state, ...data });
        },
      )
      .subscribe();
    return () => { supabase.removeChannel(channel); };
  }, [state.group_id, state.share_code]);

  const expired = useMemo(
    () => !state.unlocked_at && new Date(state.expires_at).getTime() < tick,
    [state, tick],
  );
  const unlocked = !!state.unlocked_at;
  const pct = Math.min(100, Math.round((state.count / state.threshold) * 100));
  const remaining = state.threshold - state.count;
  const countdown = formatRemaining(state.expires_at, tick);

  const share = async () => {
    const url = buildShareUrl(state.share_code);
    const text = buildShareText({ venue: venueName, discount: discountLabel, needed: Math.max(remaining, 0), windowMin });
    if (navigator.share) {
      try { await navigator.share({ title: "Drop a Spark", text, url }); return; } catch {}
    }
    await navigator.clipboard.writeText(`${text}\n${url}`);
    toast.success("Link copied — paste it in your group chat");
  };

  if (unlocked) {
    return (
      <Card className="overflow-hidden bg-ink p-6 text-ink-foreground shadow-[var(--shadow-pop)]">
        <div className="flex items-center gap-2 text-success">
          <Unlock className="h-4 w-4" />
          <p className="font-mono text-[10px] uppercase tracking-widest">Unlocked</p>
        </div>
        <p className="mt-3 font-display text-2xl font-semibold leading-tight">
          You did it. {state.count} of you cracked it open.
        </p>
        {state.claim_code && (
          <div className="mt-5 rounded-2xl bg-background/10 p-4 text-center">
            <Sparkles className="mx-auto h-5 w-5 text-primary" />
            <p className="mt-2 font-mono text-2xl font-semibold tracking-[0.3em]">{state.claim_code}</p>
            <p className="mt-1 text-xs text-ink-foreground/60">Show this at the counter</p>
          </div>
        )}
        <Button onClick={share} variant="outline" className="mt-4 w-full bg-transparent text-ink-foreground hover:bg-background/10">
          <Share2 className="h-4 w-4" /> Tell the group it's on
        </Button>
      </Card>
    );
  }

  if (expired) {
    return (
      <Card className="overflow-hidden bg-muted/40 p-6">
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Spark fizzled</p>
        <p className="mt-2 font-display text-xl font-semibold">Didn't quite make it — no charge, no stress.</p>
        <p className="mt-1 text-sm text-muted-foreground">
          {state.count} of {state.threshold} joined. Try again in a bit, or grab something else nearby.
        </p>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden bg-ink p-6 text-ink-foreground shadow-[var(--shadow-pop)]">
      <div className="flex items-center gap-2 text-primary">
        <Lock className="h-4 w-4" />
        <p className="font-mono text-[10px] uppercase tracking-widest">Spark in flight</p>
      </div>
      <p className="mt-3 font-display text-2xl font-semibold leading-tight">
        {remaining > 0 ? <>Need <span className="text-primary">{remaining}</span> more to unlock.</> : "Almost there…"}
      </p>

      {/* Progress */}
      <div className="mt-5">
        <div className="flex items-center justify-between text-xs text-ink-foreground/70">
          <span className="flex items-center gap-1.5"><Users className="h-3.5 w-3.5" /> {state.count} / {state.threshold}</span>
          <span className="flex items-center gap-1.5"><Clock className="h-3.5 w-3.5" /> {countdown} left</span>
        </div>
        <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-background/15">
          <div className="h-full bg-primary transition-all duration-500" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <Button onClick={share} className="mt-5 h-12 w-full bg-primary text-base hover:bg-primary/90">
        <Share2 className="h-4 w-4" /> Share with your group
      </Button>

      {state.claim_code && (
        <p className="mt-3 flex items-center justify-center gap-1 text-[11px] text-ink-foreground/60">
          <CheckCircle2 className="h-3 w-3 text-success" /> Your spot's saved · code <span className="font-mono">{state.claim_code}</span>
        </p>
      )}
    </Card>
  );
};

export default SparkProgressCard;
