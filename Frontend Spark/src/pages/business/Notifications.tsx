import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { usePushPermission } from "@/hooks/usePushPermission";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Bell, BellOff, BellRing, ShieldCheck, AlertCircle } from "lucide-react";
import { toast } from "sonner";

interface Prefs {
  notify_redemptions: boolean;
  notify_new_claims: boolean;
  notify_offer_expiring: boolean;
  notify_low_performance: boolean;
  notify_weekly_digest: boolean;
  notify_suggestions: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
}

const DEFAULTS: Prefs = {
  notify_redemptions: true,
  notify_new_claims: true,
  notify_offer_expiring: true,
  notify_low_performance: false,
  notify_weekly_digest: true,
  notify_suggestions: true,
  quiet_hours_start: "22:00",
  quiet_hours_end: "08:00",
};

const EVENTS: { key: keyof Prefs; title: string; desc: string }[] = [
  { key: "notify_new_claims", title: "New claims", desc: "When a customer claims one of your offers." },
  { key: "notify_redemptions", title: "Redemptions", desc: "When a SPARK code is redeemed in-store." },
  { key: "notify_offer_expiring", title: "Offer expiring", desc: "30 minutes before an active offer ends." },
  { key: "notify_suggestions", title: "AI suggestions", desc: "Fresh offer ideas tuned to your traffic." },
  { key: "notify_low_performance", title: "Low performance", desc: "If an offer underperforms its goal." },
  { key: "notify_weekly_digest", title: "Weekly digest", desc: "A short Monday recap of last week." },
];

const Notifications = ({ businessId }: { businessId: string }) => {
  const { user } = useAuth();
  const { status, request, supported } = usePushPermission();
  const [prefs, setPrefs] = useState<Prefs>(DEFAULTS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      const { data } = await supabase
        .from("business_notification_prefs")
        .select("*")
        .eq("business_id", businessId)
        .maybeSingle();
      if (!active) return;
      if (data) {
        setPrefs({
          notify_redemptions: data.notify_redemptions,
          notify_new_claims: data.notify_new_claims,
          notify_offer_expiring: data.notify_offer_expiring,
          notify_low_performance: data.notify_low_performance,
          notify_weekly_digest: data.notify_weekly_digest,
          notify_suggestions: data.notify_suggestions,
          quiet_hours_start: (data.quiet_hours_start ?? "22:00").slice(0, 5),
          quiet_hours_end: (data.quiet_hours_end ?? "08:00").slice(0, 5),
        });
      }
      setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [businessId]);

  const persist = async (next: Prefs) => {
    if (!user) return;
    setSaving(true);
    const { error } = await supabase
      .from("business_notification_prefs")
      .upsert(
        {
          business_id: businessId,
          owner_id: user.id,
          ...next,
        },
        { onConflict: "business_id" },
      );
    setSaving(false);
    if (error) {
      toast.error("Couldn't save settings");
      return;
    }
  };

  const toggle = (key: keyof Prefs) => async (value: boolean) => {
    const next = { ...prefs, [key]: value };
    setPrefs(next);
    await persist(next);
  };

  const updateQuiet = async (key: "quiet_hours_start" | "quiet_hours_end", value: string) => {
    const next = { ...prefs, [key]: value };
    setPrefs(next);
  };

  const saveQuiet = async () => {
    await persist(prefs);
    toast.success("Quiet hours updated");
  };

  if (loading) {
    return (
      <div className="container max-w-2xl py-10">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="mt-8 h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="container max-w-2xl py-6 sm:py-10">
      <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Settings</p>
      <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight sm:text-4xl">Notifications</h1>
      <p className="mt-2 text-sm text-muted-foreground sm:text-base">
        Choose what's worth interrupting you for. Spark whispers, never shouts.
      </p>

      {/* Permission card */}
      <Card className="mt-8 p-6 shadow-[var(--shadow-card)]">
        <div className="flex items-start gap-4">
          <div
            className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl ${
              status === "granted"
                ? "bg-primary/10 text-primary"
                : status === "denied"
                ? "bg-destructive/10 text-destructive"
                : "bg-muted text-muted-foreground"
            }`}
          >
            {status === "granted" ? (
              <BellRing className="h-5 w-5" />
            ) : status === "denied" ? (
              <BellOff className="h-5 w-5" />
            ) : (
              <Bell className="h-5 w-5" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="font-display text-lg font-semibold">Browser permission</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {!supported
                ? "This browser doesn't support push notifications."
                : status === "granted"
                ? "Push notifications are enabled on this device."
                : status === "denied"
                ? "Notifications are blocked. Enable them in your browser site settings."
                : "Allow Spark to send push notifications for the events you choose below."}
            </p>
            {supported && status !== "granted" && status !== "denied" && (
              <Button className="mt-4" onClick={() => request()}>
                <Bell className="h-4 w-4" /> Enable notifications
              </Button>
            )}
            {status === "denied" && (
              <div className="mt-4 flex items-start gap-2 rounded-md bg-muted p-3 text-xs text-muted-foreground">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>
                  Click the lock icon in your address bar → Site settings → Notifications → Allow.
                </span>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Event toggles */}
      <Card className="mt-6 p-6 shadow-[var(--shadow-card)]">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-muted-foreground" />
          <h2 className="font-display text-lg font-semibold">Events</h2>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">Pick the moments that deserve a tap.</p>

        <div className="mt-6 divide-y">
          {EVENTS.map(({ key, title, desc }) => (
            <div key={key} className="flex items-center justify-between gap-4 py-4 first:pt-0 last:pb-0">
              <div className="min-w-0">
                <p className="text-sm font-medium">{title}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">{desc}</p>
              </div>
              <Switch
                checked={Boolean(prefs[key])}
                onCheckedChange={toggle(key) as (v: boolean) => void}
                disabled={saving || status !== "granted"}
                aria-label={title}
              />
            </div>
          ))}
        </div>
        {status !== "granted" && (
          <p className="mt-4 text-xs text-muted-foreground">
            Enable browser permission above to receive these alerts.
          </p>
        )}
      </Card>

      {/* Quiet hours */}
      <Card className="mt-6 p-6 shadow-[var(--shadow-card)]">
        <h2 className="font-display text-lg font-semibold">Quiet hours</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          We'll hold non-urgent notifications during this window.
        </p>
        <div className="mt-5 grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="qh-start" className="text-xs">From</Label>
            <Input
              id="qh-start"
              type="time"
              value={prefs.quiet_hours_start}
              onChange={(e) => updateQuiet("quiet_hours_start", e.target.value)}
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="qh-end" className="text-xs">Until</Label>
            <Input
              id="qh-end"
              type="time"
              value={prefs.quiet_hours_end}
              onChange={(e) => updateQuiet("quiet_hours_end", e.target.value)}
              className="mt-1"
            />
          </div>
        </div>
        <Button className="mt-5" variant="outline" onClick={saveQuiet} disabled={saving}>
          Save quiet hours
        </Button>
      </Card>
    </div>
  );
};

export default Notifications;
