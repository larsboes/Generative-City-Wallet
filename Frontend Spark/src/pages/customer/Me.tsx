import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Bell, BellOff, LogOut, MapPin, Navigation, LocateFixed, Shield, Trophy } from "lucide-react";
import { toast } from "sonner";
import { usePushPermission } from "@/hooks/usePushPermission";
import { useGeolocation } from "@/hooks/useGeolocation";
import RedemptionRewards from "@/components/RedemptionRewards";

interface Prefs {
  notify_lunch: boolean;
  notify_evening: boolean;
  notify_weather: boolean;
}

const Me = () => {
  const { user, signOut } = useAuth();
  const push = usePushPermission();
  const geo = useGeolocation();
  const [prefs, setPrefs] = useState<Prefs | null>(null);
  const [name, setName] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    Promise.all([
      supabase.from("customer_prefs").select("notify_lunch, notify_evening, notify_weather").eq("user_id", user.id).maybeSingle(),
      supabase.from("profiles").select("full_name").eq("id", user.id).maybeSingle(),
    ]).then(([{ data: p }, { data: prof }]) => {
      setPrefs((p as Prefs) ?? { notify_lunch: true, notify_evening: true, notify_weather: true });
      setName(prof?.full_name ?? user.email?.split("@")[0] ?? "");
      setLoading(false);
    });
  }, [user]);

  const persist = async (next: Prefs) => {
    if (!user) return;
    const { error } = await supabase.from("customer_prefs").upsert({ user_id: user.id, ...next });
    if (error) toast.error(error.message);
  };

  const update = async (patch: Partial<Prefs>) => {
    if (!user || !prefs) return;
    const next = { ...prefs, ...patch };
    setPrefs(next);
    await persist(next);
  };

  // When a user flips a notify_* toggle ON and permission isn't granted, prompt for it.
  const updateNotify = async (patch: Partial<Prefs>) => {
    if (!prefs) return;
    const turningOn = Object.values(patch).some((v) => v === true);
    if (turningOn && push.supported && push.status !== "granted") {
      const result = await push.request();
      if (result !== "granted") {
        // Save the preference anyway, but flag that delivery is blocked
        await update(patch);
        return;
      }
    }
    await update(patch);
  };

  const enablePush = async () => {
    if (!prefs) return;
    const result = await push.request();
    if (result === "granted") {
      // Default the three channels to on once the user opts in from the banner
      const next = { ...prefs, notify_lunch: true, notify_evening: true, notify_weather: true };
      setPrefs(next);
      await persist(next);
    }
  };

  if (loading || !prefs) {
    return <div className="space-y-4 p-5"><Skeleton className="h-32" /><Skeleton className="h-48" /></div>;
  }

  const initial = (name || user?.email || "?").charAt(0).toUpperCase();

  return (
    <div className="px-5 pt-6">
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Profile</p>
      <h1 className="mt-2 font-display text-3xl font-semibold">You</h1>

      {/* Identity */}
      <Card className="mt-5 flex items-center gap-4 p-5 shadow-[var(--shadow-card)]">
        <div className="grid h-14 w-14 place-items-center rounded-full bg-primary font-display text-2xl font-semibold text-primary-foreground">
          {initial}
        </div>
        <div className="min-w-0">
          <p className="truncate font-display text-lg font-semibold">{name || "Spark user"}</p>
          <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
        </div>
      </Card>

      {/* Rewards */}
      <section className="mt-7">
        <h2 className="mb-3 flex items-center gap-2 font-display text-lg font-semibold">
          <Trophy className="h-4 w-4 text-primary" /> Rewards
        </h2>
        <RedemptionRewards />
      </section>

      {/* Location */}
      <section className="mt-7">
        <h2 className="mb-3 flex items-center gap-2 font-display text-lg font-semibold">
          <MapPin className="h-4 w-4 text-primary" /> Location
        </h2>
        <Card className="p-4">
          {geo.status === "granted" ? (
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="flex items-center gap-1.5 text-sm font-medium">
                    <LocateFixed className="h-3.5 w-3.5 text-primary" /> Precise location on
                  </p>
                  {geo.resolvedCity?.name && (
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      Currently in <span className="font-medium text-foreground">{geo.resolvedCity.name}</span>
                    </p>
                  )}
                  <p className="mt-1 text-xs text-muted-foreground">
                    Spark sorts offers by your real walking time. Coordinates stay on this device + your private profile.
                  </p>
                </div>
                <Button size="sm" variant="outline" onClick={() => { geo.clear(); toast("Location cleared"); }}>
                  Clear
                </Button>
              </div>
            </div>
          ) : geo.status === "denied" ? (
            <div>
              <p className="text-sm font-medium">Blocked by your browser</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Allow location for this site in browser settings, then reload — Spark needs it to find offers near you.
              </p>
            </div>
          ) : geo.status === "unsupported" ? (
            <p className="text-sm text-muted-foreground">This browser doesn't support precise location.</p>
          ) : (
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-medium">See how far each offer really is</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Share location once. We'll sort offers by walking time and remember it for 30 minutes.
                </p>
              </div>
              <Button size="sm" onClick={() => geo.request()}>
                <Navigation className="h-3.5 w-3.5" /> Allow
              </Button>
            </div>
          )}
        </Card>
      </section>

      {/* Notifications */}
      <section className="mt-7">
        <h2 className="mb-3 font-display text-lg font-semibold">Tell me about</h2>

        {/* Permission status banner */}
        {push.status !== "granted" && (
          <Card
            className={`mb-3 flex items-start gap-3 p-4 ${
              push.status === "denied" ? "border-destructive/40 bg-destructive/5" : "border-primary/30 bg-primary/5"
            }`}
          >
            <div className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-full bg-background">
              {push.status === "denied" ? (
                <BellOff className="h-4 w-4 text-destructive" />
              ) : (
                <Bell className="h-4 w-4 text-primary" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">
                {push.status === "unsupported" && "This browser can't deliver Spark nudges"}
                {push.status === "default" && "Turn on Spark nudges"}
                {push.status === "denied" && "Notifications are blocked"}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {push.status === "unsupported" && "Try Spark on Chrome, Safari or Firefox to receive offers in real time."}
                {push.status === "default" && "We'll only ping you when a nearby offer matches your moment."}
                {push.status === "denied" && "Allow notifications for this site in your browser settings to receive offers."}
              </p>
              {push.status === "default" && (
                <Button size="sm" className="mt-3" onClick={enablePush}>
                  <Bell className="h-3.5 w-3.5" /> Allow notifications
                </Button>
              )}
            </div>
          </Card>
        )}

        <Card className="divide-y">
          <Toggle
            label="Lunch deals"
            hint="11am – 2pm offers within walking distance"
            checked={prefs.notify_lunch}
            onChange={(v) => updateNotify({ notify_lunch: v })}
          />
          <Toggle
            label="Evening offers"
            hint="Restaurants with last-minute tables"
            checked={prefs.notify_evening}
            onChange={(v) => updateNotify({ notify_evening: v })}
          />
          <Toggle
            label="Weather-based"
            hint="A hot soup when it rains, an iced matcha when it's hot"
            checked={prefs.notify_weather}
            onChange={(v) => updateNotify({ notify_weather: v })}
          />
        </Card>

        {push.status === "granted" && (
          <p className="mt-2 px-1 text-[11px] text-muted-foreground">
            <Bell className="mr-1 inline h-3 w-3 text-primary" />
            Notifications are on for this device.
          </p>
        )}
      </section>

      {/* Explainer */}
      <section className="mt-7">
        <Accordion type="single" collapsible>
          <AccordionItem value="how" className="rounded-xl border bg-card px-4">
            <AccordionTrigger className="font-display text-base font-semibold">
              How does Spark choose what to show me?
            </AccordionTrigger>
            <AccordionContent className="text-sm text-muted-foreground">
              Spark watches the weather, the time of day and which local cafés are quieter than usual. When a merchant
              has space to fill, Spark drafts a tiny offer for the few people walking nearby — like you.
              We never share your location with merchants; only an anonymous "intent" signal makes it upstream.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="privacy" className="mt-3 rounded-xl border bg-card px-4">
            <AccordionTrigger className="font-display text-base font-semibold">
              <span className="flex items-center gap-2"><Shield className="h-4 w-4 text-primary" /> Your data, your rules</span>
            </AccordionTrigger>
            <AccordionContent className="text-sm text-muted-foreground">
              Movement and preference data stay on your device. Spark only sends an abstract "intent" to the cloud, in line with GDPR.
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </section>

      <Button variant="outline" onClick={signOut} className="mt-7 w-full">
        <LogOut className="h-4 w-4" /> Sign out
      </Button>

      <p className="mt-8 text-center text-[10px] text-muted-foreground">
        Spark · a city wallet for local merchants
      </p>
    </div>
  );
};

const Toggle = ({ label, hint, checked, onChange }: { label: string; hint: string; checked: boolean; onChange: (v: boolean) => void }) => (
  <label className="flex cursor-pointer items-center justify-between gap-4 px-4 py-3.5">
    <div className="min-w-0">
      <p className="text-sm font-medium">{label}</p>
      <p className="text-xs text-muted-foreground">{hint}</p>
    </div>
    <Switch checked={checked} onCheckedChange={onChange} />
  </label>
);

export default Me;
