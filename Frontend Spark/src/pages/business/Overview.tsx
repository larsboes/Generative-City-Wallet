import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import {
  Sparkles, MapPin, Star, ArrowRight, TrendingDown, TrendingUp, RefreshCw,
  Sun, Cloud, CloudRain, Clock, Calendar, Users, Activity, Wand2,
} from "lucide-react";
import {
  Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceArea,
} from "recharts";

interface Business {
  id: string; name: string; category: string | null; address: string | null;
  city: string | null; photo_url: string | null; rating: number | null;
}
interface HourStat { day_of_week: number; hour: number; transactions: number; revenue: number }
interface Offer {
  id: string; title: string; description: string; status: string;
  estimated_uplift: string | null; discount_label: string | null; goal: string | null;
}
interface RedeemedClaim { offer_id: string; amount_cents: number | null; redeemed_at: string }

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const Overview = ({ business }: { business: Business }) => {
  const [stats, setStats] = useState<HourStat[]>([]);
  const [offers, setOffers] = useState<Offer[]>([]);
  const [redeemed, setRedeemed] = useState<RedeemedClaim[]>([]);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);

  const load = async () => {
    const [{ data: s }, { data: o }] = await Promise.all([
      supabase.from("payone_hourly_stats")
        .select("day_of_week, hour, transactions, revenue")
        .eq("business_id", business.id),
      supabase.from("offers")
        .select("id, title, description, status, estimated_uplift, discount_label, goal")
        .eq("business_id", business.id)
        .order("created_at", { ascending: false })
        .limit(10),
    ]);
    setStats((s ?? []) as HourStat[]);
    setOffers((o ?? []) as Offer[]);

    // All redeemed claims for this business's offers (RLS allows merchants
    // to see claims on their own offers).
    const offerIds = (o ?? []).map((x: any) => x.id);
    if (offerIds.length) {
      const { data: claims } = await supabase
        .from("offer_claims")
        .select("offer_id, amount_cents, redeemed_at")
        .in("offer_id", offerIds)
        .not("redeemed_at", "is", null);
      setRedeemed((claims ?? []) as RedeemedClaim[]);
    } else {
      setRedeemed([]);
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, [business.id]);

  const seed = async () => {
    setSeeding(true);
    const { error } = await supabase.rpc("seed_payone_mock", { _business_id: business.id });
    setSeeding(false);
    if (error) return toast.error(error.message);
    toast.success("Refreshed Payone sample data");
    load();
  };

  const today = new Date();
  const todayDow = today.getDay();
  const currentHour = today.getHours();

  // Aggregations
  const { hourlyToday, hourlyAvgAll, totals, dipHour, peakHour, weekRevenue } = useMemo(() => {
    const hours = Array.from({ length: 15 }, (_, i) => i + 7);
    const todayMap = new Map<number, HourStat>();
    stats.filter((s) => s.day_of_week === todayDow).forEach((s) => todayMap.set(s.hour, s));
    const allByHour: Record<number, number[]> = {};
    stats.forEach((s) => { (allByHour[s.hour] ??= []).push(s.transactions); });

    const hourlyToday = hours.map((h) => {
      const t = todayMap.get(h)?.transactions ?? 0;
      const avgAll = allByHour[h]?.length ? allByHour[h].reduce((a, b) => a + b, 0) / allByHour[h].length : 0;
      return { hour: h, label: `${h}:00`, today: t, avg: Math.round(avgAll * 10) / 10 };
    });
    const overallAvg = hourlyToday.reduce((s, h) => s + h.avg, 0) / Math.max(1, hourlyToday.length);
    const sorted = [...hourlyToday].sort((a, b) => a.avg - b.avg);
    const dip = sorted[0];
    const peak = sorted[sorted.length - 1];
    const todayTx = hourlyToday.reduce((s, h) => s + h.today, 0);
    const todayAvgTx = hourlyToday.reduce((s, h) => s + h.avg, 0);
    const weekRev = stats.reduce((s, x) => s + Number(x.revenue), 0);

    return {
      hourlyToday,
      hourlyAvgAll: overallAvg,
      totals: { todayTx, todayAvgTx, deltaPct: todayAvgTx ? Math.round(((todayTx - todayAvgTx) / todayAvgTx) * 100) : 0 },
      dipHour: dip,
      peakHour: peak,
      weekRevenue: weekRev,
    };
  }, [stats, todayDow]);

  // Mock weather (deterministic)
  const conditions = [
    { icon: Sun, label: "Sunny", temp: 21, color: "text-amber-500" },
    { icon: Cloud, label: "Cloudy", temp: 16, color: "text-slate-500" },
    { icon: CloudRain, label: "Rainy", temp: 12, color: "text-blue-500" },
  ];
  const w = conditions[today.getDate() % conditions.length];
  const Wicon = w.icon;

  const suggestionsCount = offers.filter((o) => o.status === "suggested").length;
  const activeCount = offers.filter((o) => o.status === "active").length;

  // Spark revenue: total euros redeemed across all offers + per-offer breakdown.
  const { sparkRevenueCents, sparkRedemptions, revenueByOffer } = useMemo(() => {
    let total = 0;
    const byOffer = new Map<string, { cents: number; count: number }>();
    redeemed.forEach((c) => {
      const cents = c.amount_cents ?? 0;
      total += cents;
      const cur = byOffer.get(c.offer_id) ?? { cents: 0, count: 0 };
      cur.cents += cents;
      cur.count += 1;
      byOffer.set(c.offer_id, cur);
    });
    return {
      sparkRevenueCents: total,
      sparkRedemptions: redeemed.length,
      revenueByOffer: byOffer,
    };
  }, [redeemed]);

  // Heatmap
  const heatmapHours = Array.from({ length: 15 }, (_, i) => i + 7);
  const lookup = new Map<string, HourStat>();
  stats.forEach((s) => lookup.set(`${s.day_of_week}-${s.hour}`, s));
  const maxTx = Math.max(1, ...stats.map((s) => s.transactions));

  if (loading) {
    return (
      <div className="container max-w-6xl py-10">
        <Skeleton className="h-12 w-64" />
        <div className="mt-6 grid gap-4 md:grid-cols-4">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="mt-6 h-80" />
      </div>
    );
  }

  return (
    <div className="container max-w-6xl space-y-8 py-6 sm:space-y-10 sm:py-10">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
        <div className="min-w-0">
          <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
            {today.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" })}
          </p>
          <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight sm:text-4xl md:text-5xl">
            Good {greeting()}, <span className="italic text-primary">{firstName(business.name)}</span>.
          </h1>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground sm:text-base">
            Here's what's happening at <span className="font-medium text-foreground">{business.name}</span> today.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={seed} disabled={seeding} className="sm:size-default">
            <RefreshCw className={`h-4 w-4 ${seeding ? "animate-spin" : ""}`} /> Refresh data
          </Button>
          <Button asChild size="sm" className="sm:size-default">
            <Link to="/dashboard/offers"><Sparkles className="h-4 w-4" /> Spark suggests</Link>
          </Button>
        </div>
      </div>

      {/* Empty state for mock data */}
      {stats.length === 0 ? (
        <Card className="border-dashed bg-card/60 p-12 text-center">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-accent text-accent-foreground">
            <Activity className="h-6 w-6" />
          </div>
          <h2 className="mt-4 font-display text-2xl font-semibold">Connect your Payone terminal</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
            We'll generate a realistic 7-day sample so you can see how Spark reads your sales rhythm and finds quiet windows.
          </p>
          <Button onClick={seed} disabled={seeding} className="mt-6">
            <Sparkles className="h-4 w-4" /> Generate sample data
          </Button>
        </Card>
      ) : (
        <>
          {/* KPI strip */}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Kpi
              label="Today, so far"
              value={`${totals.todayTx}`}
              unit="transactions"
              delta={totals.deltaPct}
              accent
            />
            <Kpi
              label="Hourly average"
              value={hourlyAvgAll.toFixed(1)}
              unit="tx / hour"
            />
            <Kpi
              label="7-day revenue"
              value={`€${Math.round(weekRevenue).toLocaleString()}`}
              unit="from POS"
            />
            <Kpi
              label="Spark revenue"
              value={`€${(sparkRevenueCents / 100).toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
              unit={`${sparkRedemptions} ${sparkRedemptions === 1 ? "redemption" : "redemptions"}`}
              accent={sparkRevenueCents > 0}
            />
            <Kpi
              label="Live offers"
              value={`${activeCount}`}
              unit={`${suggestionsCount} suggested`}
            />
          </div>

          {/* Today chart + insight */}
          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2 overflow-hidden p-6 shadow-[var(--shadow-card)]">
              <div className="flex items-baseline justify-between">
                <div>
                  <h2 className="font-display text-xl font-semibold">Today's rhythm</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Transactions vs. your 7-day average. The dip is where Spark earns its keep.
                  </p>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-primary" /> Today</span>
                  <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-muted-foreground/40" /> 7-day avg</span>
                </div>
              </div>
              <div className="mt-6 h-64 w-full">
                <ResponsiveContainer>
                  <AreaChart data={hourlyToday} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="todayFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    {dipHour && (
                      <ReferenceArea x1={dipHour.label} x2={dipHour.label} strokeOpacity={0} fill="hsl(var(--primary))" fillOpacity={0.06} />
                    )}
                    <XAxis dataKey="label" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} width={32} />
                    <Tooltip
                      contentStyle={{
                        background: "hsl(var(--popover))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "0.5rem",
                        fontSize: "12px",
                      }}
                      labelStyle={{ color: "hsl(var(--foreground))", fontWeight: 600 }}
                    />
                    <Area type="monotone" dataKey="avg" stroke="hsl(var(--muted-foreground))" strokeOpacity={0.5} strokeDasharray="3 3" fill="none" name="7-day avg" />
                    <Area type="monotone" dataKey="today" stroke="hsl(var(--primary))" strokeWidth={2.5} fill="url(#todayFill)" name="Today" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Insight */}
            <Card className="flex flex-col justify-between bg-ink p-6 text-ink-foreground shadow-[var(--shadow-pop)]">
              <div>
                <Badge variant="secondary" className="bg-white/10 text-ink-foreground hover:bg-white/15">
                  <TrendingDown className="h-3 w-3" /> Opportunity
                </Badge>
                <h3 className="mt-4 font-display text-2xl font-semibold leading-tight">
                  Your slowest hour today is{" "}
                  <span className="italic text-primary-glow">
                    {dipHour ? `${dipHour.hour}:00–${dipHour.hour + 1}:00` : "—"}
                  </span>
                </h3>
                {dipHour && (
                  <p className="mt-3 text-sm leading-relaxed text-ink-foreground/70">
                    Averaging <span className="font-semibold text-ink-foreground">{dipHour.avg.toFixed(1)} tx</span> —
                    that's{" "}
                    <span className="font-semibold text-ink-foreground">
                      {Math.round(((hourlyAvgAll - dipHour.avg) / Math.max(1, hourlyAvgAll)) * 100)}%
                    </span>{" "}
                    below your daily mean. Spark can craft a 60-minute offer to fill it.
                  </p>
                )}
              </div>
              <Button asChild className="mt-6 bg-primary hover:bg-primary/90">
                <Link to="/dashboard/offers">
                  <Wand2 className="h-4 w-4" /> Generate an offer <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </Card>
          </div>

          {/* Live signals row */}
          <div>
            <div className="mb-4 flex items-baseline justify-between">
              <h2 className="font-display text-xl font-semibold">Live signals</h2>
              <p className="text-xs text-muted-foreground">refreshed continuously</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Signal icon={<Wicon className={`h-5 w-5 ${w.color}`} />} label="Weather" value={`${w.label}, ${w.temp}°C`} />
              <Signal icon={<Clock className="h-5 w-5 text-primary" />} label="Time" value={`${currentHour}:${String(today.getMinutes()).padStart(2, "0")}`} hint={currentHour >= 13 && currentHour <= 14 ? "lunch slump" : "regular hours"} />
              <Signal icon={<Calendar className="h-5 w-5 text-primary" />} label="Day" value={["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"][todayDow]} />
              <Signal icon={<Users className="h-5 w-5 text-muted-foreground" />} label="Footfall" value="Coming soon" muted />
            </div>
          </div>

          {/* Heatmap + suggestions */}
          <div className="grid gap-6 lg:grid-cols-5">
            <Card className="lg:col-span-3 p-6 shadow-[var(--shadow-card)]">
              <div className="flex items-baseline justify-between">
                <div>
                  <h2 className="font-display text-xl font-semibold">Weekly heatmap</h2>
                  <p className="mt-1 text-sm text-muted-foreground">Transactions by hour and day. Bright = busy.</p>
                </div>
                {peakHour && (
                  <div className="text-right text-xs">
                    <p className="text-muted-foreground">Peak hour</p>
                    <p className="flex items-center gap-1 font-semibold text-foreground">
                      <TrendingUp className="h-3 w-3 text-success" />
                      {peakHour.hour}:00 · {peakHour.avg.toFixed(1)} tx
                    </p>
                  </div>
                )}
              </div>
              <div className="mt-5 -mx-2 overflow-x-auto px-2">
                <div className="inline-block min-w-full">
                  <div className="flex pl-12">
                    {heatmapHours.map((h) => (
                      <div key={h} className="w-7 text-center text-[10px] text-muted-foreground">{h}</div>
                    ))}
                  </div>
                  {DAY_NAMES.map((day, di) => (
                    <div key={day} className="mt-1 flex items-center">
                      <div className="w-12 text-xs font-medium text-muted-foreground">{day}</div>
                      {heatmapHours.map((h) => {
                        const s = lookup.get(`${di}-${h}`);
                        const intensity = s ? s.transactions / maxTx : 0;
                        return (
                          <div
                            key={h}
                            className="m-[2px] grid h-6 w-6 place-items-center rounded-sm transition-transform hover:scale-110"
                            style={{
                              backgroundColor: `hsl(var(--primary) / ${0.06 + intensity * 0.85})`,
                            }}
                            title={s ? `${day} ${h}:00 — ${s.transactions} tx, €${Number(s.revenue).toFixed(0)}` : ""}
                          />
                        );
                      })}
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex items-center gap-2 pl-12 text-[10px] text-muted-foreground">
                  <span>quiet</span>
                  <div className="h-1.5 flex-1 max-w-[160px] rounded-full bg-gradient-to-r from-primary/10 to-primary" />
                  <span>busy</span>
                </div>
              </div>
            </Card>

            <Card className="lg:col-span-2 p-6 shadow-[var(--shadow-card)]">
              <div className="flex items-baseline justify-between">
                <h2 className="font-display text-xl font-semibold">Recent activity</h2>
                <Link to="/dashboard/offers" className="text-xs font-medium text-primary hover:underline">View all →</Link>
              </div>
              {offers.length === 0 ? (
                <div className="mt-6 rounded-lg border border-dashed p-6 text-center">
                  <p className="text-sm text-muted-foreground">No offers yet.</p>
                  <Button asChild size="sm" className="mt-3">
                    <Link to="/dashboard/offers"><Sparkles className="h-4 w-4" /> Generate your first</Link>
                  </Button>
                </div>
              ) : (
                <ul className="mt-4 space-y-3">
                  {offers.slice(0, 5).map((o) => {
                    const rev = revenueByOffer.get(o.id);
                    return (
                      <li key={o.id} className="flex items-start gap-3 border-b border-border/50 pb-3 last:border-0">
                        <div className={`mt-1 h-2 w-2 shrink-0 rounded-full ${
                          o.status === "active" ? "bg-success" :
                          o.status === "suggested" ? "bg-primary animate-pulse" :
                          "bg-muted-foreground/40"
                        }`} />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">{o.title}</p>
                          <p className="truncate text-xs text-muted-foreground">{o.discount_label ?? o.description}</p>
                          {rev && rev.cents > 0 && (
                            <p className="mt-0.5 text-[11px] font-medium text-success">
                              €{(rev.cents / 100).toLocaleString(undefined, { maximumFractionDigits: 2 })} from {rev.count} {rev.count === 1 ? "redemption" : "redemptions"}
                            </p>
                          )}
                        </div>
                        <Badge variant="outline" className="shrink-0 text-[10px] capitalize">{o.status}</Badge>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Card>
          </div>

          {/* Business footer card */}
          <Card className="overflow-hidden shadow-[var(--shadow-card)]">
            <div className="flex flex-col gap-6 p-6 sm:flex-row sm:items-center">
              {business.photo_url ? (
                <img src={business.photo_url} alt={business.name} className="h-20 w-20 rounded-xl object-cover" />
              ) : (
                <div className="grid h-20 w-20 place-items-center rounded-xl bg-muted text-muted-foreground">
                  <MapPin className="h-6 w-6" />
                </div>
              )}
              <div className="min-w-0 flex-1">
                <h2 className="font-display text-xl font-semibold">{business.name}</h2>
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
                  {business.category && <span>{business.category}</span>}
                  {business.address && <span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{business.address}</span>}
                  {business.rating != null && (
                    <span className="flex items-center gap-1"><Star className="h-3.5 w-3.5 fill-current text-primary" />{Number(business.rating).toFixed(1)}</span>
                  )}
                </div>
              </div>
              <Button variant="outline" asChild>
                <Link to="/dashboard/settings">Edit profile</Link>
              </Button>
            </div>
          </Card>
        </>
      )}
    </div>
  );
};

const Kpi = ({ label, value, unit, delta, accent }: {
  label: string; value: string; unit?: string; delta?: number; accent?: boolean;
}) => (
  <Card className={`min-w-0 p-5 shadow-[var(--shadow-card)] ${accent ? "border-primary/30" : ""}`}>
    <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">{label}</p>
    <div className="mt-2 flex flex-wrap items-baseline gap-x-2 gap-y-1">
      <p className="break-all font-display text-2xl font-semibold leading-none sm:text-3xl">{value}</p>
      {delta !== undefined && (
        <span className={`flex items-center gap-0.5 text-xs font-semibold ${delta >= 0 ? "text-success" : "text-primary"}`}>
          {delta >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
          {delta >= 0 ? "+" : ""}{delta}%
        </span>
      )}
    </div>
    {unit && <p className="mt-1 text-xs text-muted-foreground">{unit}</p>}
  </Card>
);

const Signal = ({ icon, label, value, hint, muted }: {
  icon: React.ReactNode; label: string; value: string; hint?: string; muted?: boolean;
}) => (
  <Card className={`flex items-center gap-4 p-4 shadow-sm ${muted ? "opacity-60" : ""}`}>
    <div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-accent">{icon}</div>
    <div className="min-w-0">
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">{label}</p>
      <p className="truncate font-semibold">{value}</p>
      {hint && <p className="truncate text-[11px] text-muted-foreground">{hint}</p>}
    </div>
  </Card>
);

const greeting = () => {
  const h = new Date().getHours();
  if (h < 12) return "morning";
  if (h < 18) return "afternoon";
  return "evening";
};
const firstName = (name: string) => name.split(/[\s,]/)[0];

export default Overview;
