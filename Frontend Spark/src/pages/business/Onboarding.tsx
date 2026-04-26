import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/hooks/use-toast";
import { Check, MapPin, Star, Sparkles, ArrowLeft, Search } from "lucide-react";

const CATEGORIES = [
  "Restaurant", "Café", "Bakery", "Bar", "Pub", "Coffee Shop",
  "Fast Food", "Pizzeria", "Ice Cream Shop", "Dessert Shop",
  "Tea House", "Juice Bar", "Food Truck", "Bistro", "Other",
] as const;

const matchCategory = (raw: string | null | undefined): string => {
  if (!raw) return "";
  const lower = raw.toLowerCase();
  return CATEGORIES.find((c) => lower.includes(c.toLowerCase())) ?? "Other";
};

interface Match {
  placeId: string | null;
  name: string;
  category: string | null;
  address: string;
  city: string | null;
  country: string | null;
  latitude: number | null;
  longitude: number | null;
  phone: string | null;
  website: string | null;
  photoUrl: string | null;
  rating: number | null;
  priceLevel: number | null;
  openingHours: any;
  raw: any;
}

type Step = 1 | 2 | 3;

const Onboarding = () => {
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  const [step, setStep] = useState<Step>(1);

  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [searching, setSearching] = useState(false);
  const [matches, setMatches] = useState<Match[]>([]);
  const [selected, setSelected] = useState<Match | null>(null);

  // Editable form state for step 3
  const [form, setForm] = useState<Partial<Match>>({});
  const [saving, setSaving] = useState(false);

  // If business already onboarded, go to dashboard
  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    supabase.from("businesses").select("id, onboarding_completed").eq("owner_id", user.id).maybeSingle()
      .then(({ data }) => {
        if (cancelled) return;
        if (data?.onboarding_completed) navigate("/dashboard", { replace: true });
      });
    return () => { cancelled = true; };
  }, [user, navigate]);

  const search = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !location.trim()) return;
    setSearching(true);
    setMatches([]);
    try {
      const { data, error } = await supabase.functions.invoke("lookup-business", {
        body: { name: name.trim(), location: location.trim() },
      });
      if (error) throw error;
      const list = (data?.matches ?? []) as Match[];
      setMatches(list);
      setStep(2);
      if (list.length === 0) {
        toast({ title: "No matches found", description: "You can enter your business details manually." });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Lookup failed";
      toast({ title: "Couldn't reach Google Places", description: msg, variant: "destructive" });
    } finally {
      setSearching(false);
    }
  };

  const pickMatch = (m: Match | null) => {
    setSelected(m);
    const base = m ?? ({ name, address: location } as Partial<Match>);
    setForm({ ...base, category: matchCategory(base.category ?? null) });
    setStep(3);
  };

  const save = async () => {
    if (!user) return;
    if (!form.name || form.name.trim().length === 0) {
      toast({ title: "Business name required", variant: "destructive" });
      return;
    }
    setSaving(true);
    try {
      const payload = {
        owner_id: user.id,
        name: form.name!,
        category: form.category ?? null,
        address: form.address ?? null,
        city: form.city ?? null,
        country: form.country ?? null,
        latitude: form.latitude ?? null,
        longitude: form.longitude ?? null,
        phone: form.phone ?? null,
        website: form.website ?? null,
        photo_url: form.photoUrl ?? null,
        price_level: form.priceLevel ?? null,
        rating: form.rating ?? null,
        opening_hours: form.openingHours ?? null,
        google_place_id: form.placeId ?? null,
        raw_place_data: selected?.raw ?? null,
        onboarding_completed: true,
      };
      const { error } = await supabase.from("businesses").upsert(payload, { onConflict: "owner_id" } as any);
      // upsert with non-unique owner_id falls back to insert; handle gracefully:
      if (error) {
        // try plain insert
        const { error: e2 } = await supabase.from("businesses").insert(payload);
        if (e2) throw e2;
      }
      toast({ title: "You're all set", description: "Welcome to Spark." });
      navigate("/dashboard", { replace: true });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Save failed";
      toast({ title: "Couldn't save your business", description: msg, variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-muted/30">
      <header className="border-b bg-background">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="grid h-8 w-8 place-items-center rounded-md bg-primary text-primary-foreground">
              <Sparkles className="h-4 w-4" />
            </div>
            <span className="font-semibold">Spark</span>
          </div>
          <Button variant="ghost" size="sm" onClick={signOut}>Sign out</Button>
        </div>
      </header>

      <main className="container max-w-3xl py-12">
        {/* Step indicator */}
        <div className="mb-8 flex items-center gap-2">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex flex-1 items-center gap-2">
              <div className={`grid h-7 w-7 place-items-center rounded-full text-xs font-medium ${
                step >= s ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
              }`}>{step > s ? <Check className="h-3.5 w-3.5" /> : s}</div>
              {s < 3 && <div className={`h-px flex-1 ${step > s ? "bg-primary" : "bg-border"}`} />}
            </div>
          ))}
        </div>

        {step === 1 && (
          <Card className="shadow-[var(--shadow-card)]">
            <CardHeader>
              <CardTitle>Find your business</CardTitle>
              <CardDescription>We'll pull your details from Google so you don't have to type them.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={search} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="bname">Business name</Label>
                  <Input id="bname" value={name} onChange={(e) => setName(e.target.value)} placeholder="Café Müller" maxLength={200} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="bloc">City or address</Label>
                  <Input id="bloc" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Stuttgart, Germany" maxLength={200} required />
                </div>
                <Button type="submit" size="lg" className="w-full" disabled={searching}>
                  <Search className="h-4 w-4" />
                  {searching ? "Searching Google Places…" : "Find my business"}
                </Button>
              </form>
            </CardContent>
          </Card>
        )}

        {step === 2 && (
          <Card className="shadow-[var(--shadow-card)]">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Pick the right one</CardTitle>
                  <CardDescription>Select your business from the matches below.</CardDescription>
                </div>
                <Button variant="ghost" size="sm" onClick={() => setStep(1)}>
                  <ArrowLeft className="h-4 w-4" /> Back
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {searching && <><Skeleton className="h-24 w-full" /><Skeleton className="h-24 w-full" /></>}
              {!searching && matches.length === 0 && (
                <p className="text-sm text-muted-foreground">No matches found. You can enter details manually.</p>
              )}
              {matches.map((m, i) => (
                <button
                  key={(m.placeId ?? "") + i}
                  onClick={() => pickMatch(m)}
                  className="flex w-full gap-4 rounded-lg border bg-card p-4 text-left transition-colors hover:border-primary hover:bg-accent/30"
                >
                  {m.photoUrl ? (
                    <img src={m.photoUrl} alt={m.name} className="h-20 w-20 rounded-md object-cover" />
                  ) : (
                    <div className="grid h-20 w-20 place-items-center rounded-md bg-muted text-muted-foreground">
                      <MapPin className="h-5 w-5" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="truncate font-medium">{m.name}</h3>
                      {m.rating != null && (
                        <span className="flex shrink-0 items-center gap-1 text-sm text-muted-foreground">
                          <Star className="h-3.5 w-3.5 fill-current text-primary" />{Number(m.rating).toFixed(1)}
                        </span>
                      )}
                    </div>
                    {m.category && <p className="text-sm text-muted-foreground">{m.category}</p>}
                    <p className="mt-1 truncate text-sm text-muted-foreground">{m.address}</p>
                  </div>
                </button>
              ))}
              <button
                onClick={() => pickMatch(null)}
                className="w-full rounded-lg border border-dashed p-4 text-sm text-muted-foreground transition-colors hover:border-primary hover:text-foreground"
              >
                None of these — enter details manually
              </button>
            </CardContent>
          </Card>
        )}

        {step === 3 && (
          <Card className="shadow-[var(--shadow-card)]">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Confirm your details</CardTitle>
                  <CardDescription>Edit anything that needs a tweak before going live.</CardDescription>
                </div>
                <Button variant="ghost" size="sm" onClick={() => setStep(2)}>
                  <ArrowLeft className="h-4 w-4" /> Back
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {form.photoUrl && (
                <img src={form.photoUrl} alt={form.name ?? ""} className="h-40 w-full rounded-md object-cover" />
              )}
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Business name" value={form.name ?? ""} onChange={(v) => setForm({ ...form, name: v })} />
                <div className="space-y-2">
                  <Label>Category</Label>
                  <Select value={form.category ?? ""} onValueChange={(v) => setForm({ ...form, category: v })}>
                    <SelectTrigger><SelectValue placeholder="Select a category" /></SelectTrigger>
                    <SelectContent>
                      {CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="sm:col-span-2">
                  <Field label="Address" value={form.address ?? ""} onChange={(v) => setForm({ ...form, address: v })} />
                </div>
                <Field label="City" value={form.city ?? ""} onChange={(v) => setForm({ ...form, city: v })} />
                <Field label="Country" value={form.country ?? ""} onChange={(v) => setForm({ ...form, country: v })} />
                <Field label="Phone" value={form.phone ?? ""} onChange={(v) => setForm({ ...form, phone: v })} />
                <Field label="Website" value={form.website ?? ""} onChange={(v) => setForm({ ...form, website: v })} />
              </div>
              <Button onClick={save} size="lg" className="w-full" disabled={saving}>
                {saving ? "Saving…" : "Confirm and continue"}
              </Button>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
};

const Field = ({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) => (
  <div className="space-y-2">
    <Label>{label}</Label>
    <Input value={value} onChange={(e) => onChange(e.target.value)} maxLength={300} />
  </div>
);

export default Onboarding;
