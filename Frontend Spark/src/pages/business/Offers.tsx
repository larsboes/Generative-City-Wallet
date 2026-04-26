import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Sparkles, Wand2, Clock, Users, TrendingUp, Plus, Check, X, Pause, Play, Lock } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";

interface Offer {
  id: string;
  title: string;
  description: string;
  goal: string | null;
  discount_label: string | null;
  items: string | null;
  start_time: string | null;
  end_time: string | null;
  audience: string | null;
  estimated_uplift: string | null;
  reasoning: string | null;
  source: string;
  status: "suggested" | "active" | "paused" | "expired" | "dismissed";
  accepted_count: number;
  views_count: number;
  created_at: string;
  is_locked?: boolean;
  unlock_threshold?: number | null;
  unlock_window_minutes?: number | null;
}

const GOAL_LABELS: Record<string, string> = {
  fill_quiet_window: "Fill a quiet window",
  weather_react: "React to weather",
  win_back: "Win back regulars",
  acquire_locals: "Acquire new locals",
  move_stock: "Move specific stock",
  event_capture: "Capture local event",
};

const Offers = ({ businessId }: { businessId: string }) => {
  const { user } = useAuth();
  const [offers, setOffers] = useState<Offer[]>([]);
  const [revenueByOffer, setRevenueByOffer] = useState<Map<string, { cents: number; count: number }>>(new Map());
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);

  const load = async () => {
    const { data } = await supabase
      .from("offers")
      .select("*")
      .eq("business_id", businessId)
      .order("created_at", { ascending: false });
    const list = (data ?? []) as Offer[];
    setOffers(list);

    const ids = list.map((o) => o.id);
    if (ids.length) {
      const { data: claims } = await supabase
        .from("offer_claims")
        .select("offer_id, amount_cents")
        .in("offer_id", ids)
        .not("redeemed_at", "is", null);
      const map = new Map<string, { cents: number; count: number }>();
      (claims ?? []).forEach((c: any) => {
        const cur = map.get(c.offer_id) ?? { cents: 0, count: 0 };
        cur.cents += c.amount_cents ?? 0;
        cur.count += 1;
        map.set(c.offer_id, cur);
      });
      setRevenueByOffer(map);
    } else {
      setRevenueByOffer(new Map());
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, [businessId]);

  const generateSuggestions = async () => {
    setGenerating(true);
    try {
      // Ensure mock data is seeded
      await supabase.rpc("seed_payone_mock", { _business_id: businessId });
      const { data, error } = await supabase.functions.invoke("suggest-offers");
      if (error) throw error;
      if ((data as any)?.error) throw new Error((data as any).error);
      toast.success(`${(data as any).suggestions?.length ?? 0} new suggestions ready`);
      await load();
    } catch (e: any) {
      toast.error(e.message ?? "Failed to generate suggestions");
    } finally {
      setGenerating(false);
    }
  };

  const updateStatus = async (id: string, status: Offer["status"]) => {
    const patch: any = { status };
    if (status === "active") patch.launched_at = new Date().toISOString();
    const { error } = await supabase.from("offers").update(patch).eq("id", id);
    if (error) return toast.error(error.message);
    toast.success(
      status === "active" ? "Offer launched" : status === "dismissed" ? "Dismissed" : status === "paused" ? "Paused" : "Updated",
    );
    load();
  };

  const suggested = offers.filter((o) => o.status === "suggested");
  const active = offers.filter((o) => o.status === "active" || o.status === "paused");
  const past = offers.filter((o) => o.status === "expired" || o.status === "dismissed");

  return (
    <div className="container max-w-6xl py-6 sm:py-10">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Offers</p>
          <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight sm:text-4xl md:text-5xl">
            Generative <span className="italic text-primary">offers</span>
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-muted-foreground sm:text-base">
            Spark reads your Payone data and live context, then drafts offers timed to fill the exact hour you need them.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => setWizardOpen(true)} className="sm:size-default">
            <Plus className="h-4 w-4" /> New offer
          </Button>
          <Button onClick={generateSuggestions} disabled={generating} size="sm" className="sm:size-default">
            <Sparkles className="h-4 w-4" />
            {generating ? "Thinking…" : "Spark suggests"}
          </Button>
        </div>
      </div>

      {/* AI suggestions */}
      <section className="mt-10">
        <div className="mb-4 flex items-center gap-2">
          <Wand2 className="h-4 w-4 text-primary" />
          <h2 className="text-lg font-semibold">Spark suggests for you</h2>
          {suggested.length > 0 && <Badge variant="secondary">{suggested.length}</Badge>}
        </div>
        {loading ? (
          <div className="grid gap-4 md:grid-cols-2"><Skeleton className="h-56" /><Skeleton className="h-56" /></div>
        ) : suggested.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
              <div className="grid h-12 w-12 place-items-center rounded-full bg-accent text-accent-foreground">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <p className="font-medium">No suggestions yet</p>
                <p className="text-sm text-muted-foreground">Click "Spark suggests" to generate AI-powered offer ideas based on your sales data.</p>
              </div>
              <Button onClick={generateSuggestions} disabled={generating}>
                <Sparkles className="h-4 w-4" /> {generating ? "Thinking…" : "Generate suggestions"}
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {suggested.map((o) => (
              <SuggestionCard key={o.id} offer={o} onLaunch={() => updateStatus(o.id, "active")} onDismiss={() => updateStatus(o.id, "dismissed")} />
            ))}
          </div>
        )}
      </section>

      {/* Active */}
      <section className="mt-12">
        <h2 className="mb-4 text-lg font-semibold">Active offers <span className="text-sm font-normal text-muted-foreground">({active.length})</span></h2>
        {active.length === 0 ? (
          <p className="text-sm text-muted-foreground">No live offers right now.</p>
        ) : (
          <div className="grid gap-3">
            {active.map((o) => (
              <ActiveOfferRow
                key={o.id}
                offer={o}
                revenue={revenueByOffer.get(o.id)}
                onToggle={() => updateStatus(o.id, o.status === "active" ? "paused" : "active")}
                onEnd={() => updateStatus(o.id, "expired")}
              />
            ))}
          </div>
        )}
      </section>

      {/* Past */}
      {past.length > 0 && (
        <section className="mt-12">
          <h2 className="mb-4 text-lg font-semibold">Past offers <span className="text-sm font-normal text-muted-foreground">({past.length})</span></h2>
          <div className="grid gap-2">
            {past.map((o) => (
              <div key={o.id} className="flex items-center justify-between rounded-md border bg-card px-4 py-2 text-sm">
                <div className="flex items-center gap-3">
                  <span className="font-medium">{o.title}</span>
                  <span className="text-muted-foreground">{o.discount_label}</span>
                </div>
                <Badge variant="outline" className="capitalize">{o.status}</Badge>
              </div>
            ))}
          </div>
        </section>
      )}

      <NewOfferWizard open={wizardOpen} onOpenChange={setWizardOpen} businessId={businessId} ownerId={user!.id} onCreated={load} />
    </div>
  );
};

const SuggestionCard = ({ offer, onLaunch, onDismiss }: { offer: Offer; onLaunch: () => void; onDismiss: () => void }) => (
  <Card className="overflow-hidden border-primary/20 shadow-[var(--shadow-card)] transition-shadow hover:shadow-md">
    <CardHeader>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          {offer.goal && (
            <Badge variant="secondary" className="mb-2 gap-1">
              <Sparkles className="h-3 w-3" /> {GOAL_LABELS[offer.goal] ?? offer.goal}
            </Badge>
          )}
          <CardTitle className="text-lg">{offer.title}</CardTitle>
          <CardDescription className="mt-1">{offer.description}</CardDescription>
        </div>
        {offer.estimated_uplift && (
          <div className="shrink-0 rounded-md bg-primary/10 px-2.5 py-1 text-right">
            <p className="text-[10px] uppercase tracking-wide text-primary">Est. impact</p>
            <p className="text-sm font-semibold text-primary">{offer.estimated_uplift}</p>
          </div>
        )}
      </div>
    </CardHeader>
    <CardContent className="space-y-3">
      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
        {offer.discount_label && <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5"><TrendingUp className="h-3 w-3" />{offer.discount_label}</span>}
        {offer.start_time && offer.end_time && <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5"><Clock className="h-3 w-3" />{offer.start_time.slice(0,5)}–{offer.end_time.slice(0,5)}</span>}
        {offer.audience && <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5"><Users className="h-3 w-3" />{offer.audience}</span>}
      </div>
      {offer.reasoning && (
        <p className="rounded-md border-l-2 border-primary/40 bg-muted/50 px-3 py-2 text-xs italic text-muted-foreground">
          {offer.reasoning}
        </p>
      )}
      <div className="flex gap-2 pt-2">
        <Button size="sm" onClick={onLaunch} className="flex-1"><Check className="h-4 w-4" /> Launch</Button>
        <Button size="sm" variant="ghost" onClick={onDismiss}><X className="h-4 w-4" /> Dismiss</Button>
      </div>
    </CardContent>
  </Card>
);

const ActiveOfferRow = ({
  offer, revenue, onToggle, onEnd,
}: {
  offer: Offer;
  revenue?: { cents: number; count: number };
  onToggle: () => void;
  onEnd: () => void;
}) => (
  <Card className="shadow-sm">
    <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={offer.status === "active" ? "default" : "secondary"} className="capitalize">{offer.status}</Badge>
          {offer.is_locked && (
            <Badge variant="outline" className="gap-1 border-foreground/30">
              <Lock className="h-3 w-3" /> Spark · {offer.unlock_threshold ?? 4} in {offer.unlock_window_minutes ?? 30}m
            </Badge>
          )}
          <h3 className="min-w-0 truncate font-medium">{offer.title}</h3>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">{offer.description}</p>
        <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
          {offer.discount_label && <span>{offer.discount_label}</span>}
          {offer.start_time && offer.end_time && <span>{offer.start_time.slice(0,5)}–{offer.end_time.slice(0,5)}</span>}
          {offer.audience && <span>{offer.audience}</span>}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-4 sm:gap-6">
        <div className="text-center">
          <p className="text-xs text-muted-foreground">Views</p>
          <p className="text-lg font-semibold">{offer.views_count}</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-muted-foreground">Redeemed</p>
          <p className="text-lg font-semibold">{revenue?.count ?? 0}</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-muted-foreground">Revenue</p>
          <p className={`text-lg font-semibold ${revenue && revenue.cents > 0 ? "text-success" : ""}`}>
            €{((revenue?.cents ?? 0) / 100).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={onToggle}>
            {offer.status === "active" ? <><Pause className="h-4 w-4" /> Pause</> : <><Play className="h-4 w-4" /> Resume</>}
          </Button>
          <Button size="sm" variant="ghost" onClick={onEnd}>End</Button>
        </div>
      </div>
    </div>
  </Card>
);

const NewOfferWizard = ({
  open, onOpenChange, businessId, ownerId, onCreated,
}: { open: boolean; onOpenChange: (v: boolean) => void; businessId: string; ownerId: string; onCreated: () => void }) => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [goal, setGoal] = useState<string>("fill_quiet_window");
  const [discount, setDiscount] = useState("");
  const [start, setStart] = useState("13:00");
  const [end, setEnd] = useState("14:00");
  const [audience, setAudience] = useState("Within 400m");
  const [saving, setSaving] = useState(false);
  const [isLocked, setIsLocked] = useState(false);
  const [threshold, setThreshold] = useState(4);
  const [windowMin, setWindowMin] = useState(30);

  const reset = () => {
    setTitle(""); setDescription(""); setDiscount(""); setStart("13:00"); setEnd("14:00");
    setAudience("Within 400m"); setGoal("fill_quiet_window");
    setIsLocked(false); setThreshold(4); setWindowMin(30);
  };

  const submit = async (launch: boolean) => {
    if (!title || !description) {
      toast.error("Title and description are required");
      return;
    }
    setSaving(true);
    const { error } = await supabase.from("offers").insert({
      business_id: businessId, owner_id: ownerId,
      title, description, goal, discount_label: discount || null,
      start_time: start, end_time: end, audience,
      source: "manual",
      status: launch ? "active" : "suggested",
      launched_at: launch ? new Date().toISOString() : null,
      is_locked: isLocked,
      unlock_threshold: isLocked ? threshold : null,
      unlock_window_minutes: isLocked ? windowMin : null,
    });
    setSaving(false);
    if (error) return toast.error(error.message);
    toast.success(launch ? "Offer launched" : "Saved as draft");
    reset();
    onOpenChange(false);
    onCreated();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-lg overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create a new offer</DialogTitle>
          <DialogDescription>Define your goal — Spark will help you reach it.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label>Goal</Label>
            <Select value={goal} onValueChange={setGoal}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {Object.entries(GOAL_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Title</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Lunch combo €6" />
          </div>
          <div className="space-y-1.5">
            <Label>Description</Label>
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Coffee + pastry combo for €6 — 1 to 2 PM only" rows={2} />
          </div>
          <div className="space-y-1.5">
            <Label>Discount label</Label>
            <Input value={discount} onChange={(e) => setDiscount(e.target.value)} placeholder="-20% lunch combo" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5"><Label>Start</Label><Input type="time" value={start} onChange={(e) => setStart(e.target.value)} /></div>
            <div className="space-y-1.5"><Label>End</Label><Input type="time" value={end} onChange={(e) => setEnd(e.target.value)} /></div>
          </div>
          <div className="space-y-1.5">
            <Label>Audience</Label>
            <Input value={audience} onChange={(e) => setAudience(e.target.value)} />
          </div>

          {/* Locked offer / Spark */}
          <div className="rounded-lg border bg-muted/30 p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-2">
                <Lock className="mt-0.5 h-4 w-4 text-primary" />
                <div>
                  <Label className="text-sm font-medium">Make this a Spark (group unlock)</Label>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Customers must rally friends to unlock the deal — they share, you fill the room.
                  </p>
                </div>
              </div>
              <Switch checked={isLocked} onCheckedChange={setIsLocked} />
            </div>
            {isLocked && (
              <>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label className="text-xs">People to unlock</Label>
                    <Input
                      type="number" min={2} max={20}
                      value={threshold}
                      onChange={(e) => setThreshold(Math.max(2, Math.min(20, Number(e.target.value) || 2)))}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Window</Label>
                    <Select value={String(windowMin)} onValueChange={(v) => setWindowMin(Number(v))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="15">15 minutes</SelectItem>
                        <SelectItem value="30">30 minutes</SelectItem>
                        <SelectItem value="60">60 minutes</SelectItem>
                        <SelectItem value="120">2 hours</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <p className="mt-3 rounded-md bg-background/60 px-3 py-2 text-xs italic text-muted-foreground">
                  "I'm here! If {Math.max(0, threshold - 1)} more join in the next {windowMin} min, we all unlock {discount || "this offer"}."
                </p>
              </>
            )}
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => submit(false)} disabled={saving}>Save as draft</Button>
          <Button onClick={() => submit(true)} disabled={saving}>Launch now</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default Offers;
