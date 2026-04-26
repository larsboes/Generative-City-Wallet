import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { z } from "zod";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle2, ScanLine, XCircle, AlertCircle, RotateCcw, Clock, Camera, Sparkles, Euro } from "lucide-react";
import { toast } from "sonner";
import CodeScanner from "@/components/CodeScanner";
import { DEMO_CLAIM_CODE, isDemoClaimCode, markDemoClaimRedeemed } from "@/lib/demoOffer";

// Code shape on the customer side: SPARK-XXXX (4 alphanum chars).
// We accept users typing or scanning either "SPARK-A4F2" or just "A4F2".
const codeSchema = z
  .string()
  .trim()
  .toUpperCase()
  .transform((v) => v.replace(/^SPARK[-\s]?/i, ""))
  .pipe(
    z
      .string()
      .regex(/^[A-Z0-9]{4}$/, { message: "Codes are 4 letters or numbers, e.g. A4F2" })
  );

interface ClaimRow {
  id: string;
  code: string;
  user_id: string;
  offer_id: string;
  claimed_at: string;
  redeemed_at: string | null;
}

interface OfferRow {
  id: string;
  title: string;
  description: string;
  discount_label: string | null;
  end_time: string | null;
  status: string;
}

type LookupResult =
  | { kind: "ok"; claim: ClaimRow; offer: OfferRow }
  | { kind: "already"; claim: ClaimRow; offer: OfferRow }
  | { kind: "demo_redeemed"; code: string }
  | { kind: "not_found" }
  | { kind: "wrong_business" }
  | { kind: "error"; message: string };

interface RecentEntry {
  code: string;
  title: string;
  redeemedAt: string;
}

const Redeem = ({ businessId }: { businessId: string }) => {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<LookupResult | null>(null);
  const [recent, setRecent] = useState<RecentEntry[]>([]);
  const [loadingRecent, setLoadingRecent] = useState(true);
  const [scannerOpen, setScannerOpen] = useState(false);
  const [hasOffers, setHasOffers] = useState<boolean | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load this merchant's recent redemptions
  const loadRecent = async () => {
    setLoadingRecent(true);
    const { data: claims } = await supabase
      .from("offer_claims")
      .select("id, code, offer_id, redeemed_at")
      .not("redeemed_at", "is", null)
      .order("redeemed_at", { ascending: false })
      .limit(8);

    const offerIds = Array.from(new Set((claims ?? []).map((c) => c.offer_id)));
    let titles = new Map<string, string>();
    if (offerIds.length) {
      const { data: offers } = await supabase
        .from("offers")
        .select("id, title")
        .in("id", offerIds);
      (offers ?? []).forEach((o: any) => titles.set(o.id, o.title));
    }
    setRecent(
      (claims ?? []).map((c: any) => ({
        code: c.code,
        title: titles.get(c.offer_id) ?? "Offer",
        redeemedAt: c.redeemed_at,
      }))
    );
    setLoadingRecent(false);
  };

  useEffect(() => {
    loadRecent();
    inputRef.current?.focus();
    // Check whether this business has any offers at all (any status).
    // If not, we surface an empty-state CTA instead of the redeem UI.
    supabase
      .from("offers")
      .select("id", { count: "exact", head: true })
      .eq("business_id", businessId)
      .then(({ count }) => setHasOffers((count ?? 0) > 0));
  }, [businessId]);

  const reset = () => {
    setCode("");
    setError(null);
    setResult(null);
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  // Mark a verified claim as redeemed with the order amount. Returns true on success.
  const markRedeemed = async (
    claimId: string,
    offerTitle: string,
    amountCents: number,
  ): Promise<boolean> => {
    const { data, error: updErr } = await supabase
      .from("offer_claims")
      .update({ redeemed_at: new Date().toISOString(), amount_cents: amountCents })
      .eq("id", claimId)
      .is("redeemed_at", null) // guard against double-redeem races
      .select("id, redeemed_at")
      .maybeSingle();
    if (updErr) {
      toast.error(updErr.message);
      return false;
    }
    if (!data) {
      toast.error("This code was already redeemed.");
      return false;
    }
    // Award Spark points to the customer (1 € = 1 point, min 1).
    const { data: pts, error: ptsErr } = await supabase.rpc(
      "award_redemption_points",
      { _claim_id: claimId },
    );
    if (ptsErr) {
      // Don't block the redemption — just log + warn.
      console.warn("award_redemption_points failed", ptsErr.message);
      toast.success(`Redeemed €${(amountCents / 100).toFixed(2)} · ${offerTitle}`);
    } else {
      toast.success(
        `Redeemed €${(amountCents / 100).toFixed(2)} · ${offerTitle} · +${pts ?? 0} pts`,
      );
    }
    return true;
  };

  const verify = async (raw: string, opts?: { fromScan?: boolean }) => {
    setError(null);
    setResult(null);
    const parsed = codeSchema.safeParse(raw);
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Invalid code");
      return;
    }
    const cleaned = parsed.data;
    // Stable demo QR — never hits the DB. Auto-redeems silently with no price prompt.
    if (isDemoClaimCode(cleaned)) {
      const redeemedAt = new Date().toISOString();
      setResult({ kind: "demo_redeemed", code: cleaned });
      markDemoClaimRedeemed();
      supabase
        .from("demo_redemptions" as any)
        .upsert({ code: DEMO_CLAIM_CODE, redeemed_at: redeemedAt } as any, { onConflict: "code" })
        .then(({ error }) => {
          if (error) console.warn("Failed to sync demo redemption", error.message);
        });
      toast.success(`Redeemed · Cold drink on us — 10% off`);
      return;
    }
    setBusy(true);
    try {
      const { data: claims, error: claimErr } = await supabase
        .from("offer_claims")
        .select("id, code, user_id, offer_id, claimed_at, redeemed_at")
        .in("code", [cleaned, `SPARK-${cleaned}`])
        .order("claimed_at", { ascending: false })
        .limit(1);
      const claim = claims?.[0] ?? null;

      if (claimErr) {
        setResult({ kind: "error", message: claimErr.message });
        return;
      }
      if (!claim) {
        setResult({ kind: "not_found" });
        return;
      }

      const { data: offer } = await supabase
        .from("offers")
        .select("id, title, description, discount_label, end_time, status, business_id")
        .eq("id", claim.offer_id)
        .maybeSingle();

      if (!offer) {
        setResult({ kind: "error", message: "Offer not found" });
        return;
      }
      if ((offer as any).business_id !== businessId) {
        setResult({ kind: "wrong_business" });
        return;
      }

      if (claim.redeemed_at) {
        setResult({ kind: "already", claim: claim as ClaimRow, offer: offer as OfferRow });
        return;
      }

      setResult({ kind: "ok", claim: claim as ClaimRow, offer: offer as OfferRow });
    } finally {
      setBusy(false);
    }
  };

  const confirmRedeem = async (amountCents: number) => {
    if (result?.kind !== "ok") return;
    setBusy(true);
    const ok = await markRedeemed(result.claim.id, result.offer.title, amountCents);
    setBusy(false);
    if (!ok) {
      setResult({ ...result, kind: "already" });
      return;
    }
    loadRecent();
    reset();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    verify(code);
  };

  // No offers yet — guide the merchant to the wizard before they can redeem anything.
  if (hasOffers === false) {
    return (
      <div className="container max-w-2xl py-10">
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Counter</p>
        <h1 className="mt-2 font-display text-4xl font-semibold tracking-tight">Redeem a Spark code</h1>

        <Card className="mt-7 p-8 text-center shadow-[var(--shadow-card)]">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-primary/10">
            <Sparkles className="h-6 w-6 text-primary" />
          </div>
          <h2 className="mt-4 font-display text-xl font-semibold">No offers to redeem yet</h2>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground">
            Customers can only get a Spark code once you've launched at least one offer.
            Create your first one and the codes will start arriving here.
          </p>
          <Button asChild className="mt-5">
            <Link to="/dashboard/offers">
              <Sparkles className="h-4 w-4" /> Create your first offer
            </Link>
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="container max-w-2xl py-6 sm:py-10">
      <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Counter</p>
      <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight sm:text-4xl">Redeem a Spark code</h1>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        Scan the QR on the customer's wallet, or type the four-character code below — we'll mark it redeemed.
      </p>

      {/* Entry */}
      <Card className="mt-7 p-6 shadow-[var(--shadow-card)]">
        <Button
          type="button"
          onClick={() => setScannerOpen(true)}
          className="h-12 w-full"
          variant="default"
        >
          <Camera className="h-4 w-4" /> Scan QR with camera
        </Button>

        <div className="my-5 flex items-center gap-3 text-[10px] uppercase tracking-widest text-muted-foreground">
          <span className="h-px flex-1 bg-border" />
          or enter manually
          <span className="h-px flex-1 bg-border" />
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="code" className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              Spark code
            </label>
            <div className="mt-2 flex items-stretch gap-2">
              <div className="relative flex-1">
                <ScanLine className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="code"
                  ref={inputRef}
                  value={code}
                  onChange={(e) => {
                    setError(null);
                    const v = e.target.value.toUpperCase().replace(/[^A-Z0-9-]/g, "").slice(0, 12);
                    setCode(v);
                  }}
                  placeholder="A4F2"
                  autoComplete="off"
                  autoCapitalize="characters"
                  spellCheck={false}
                  inputMode="text"
                  maxLength={12}
                  aria-invalid={!!error}
                  className="h-12 pl-9 font-mono text-lg tracking-[0.3em]"
                />
              </div>
              <Button type="submit" disabled={busy || code.trim().length < 4} className="h-12 min-w-28">
                {busy ? "Checking…" : "Verify"}
              </Button>
            </div>
            {error && (
              <p className="mt-2 flex items-center gap-1.5 text-xs text-destructive">
                <AlertCircle className="h-3.5 w-3.5" /> {error}
              </p>
            )}
          </div>
        </form>

        {/* Result */}
        {result && (
          <div className="mt-6 border-t pt-6">
            <ResultCard result={result} onConfirm={confirmRedeem} onReset={reset} busy={busy} />
          </div>
        )}
      </Card>

      <CodeScanner
        open={scannerOpen}
        onOpenChange={setScannerOpen}
        onCode={(scanned) => {
          setCode(scanned);
          // Scanned via camera → look it up; merchant then enters the order amount.
          verify(scanned);
        }}
      />

      {/* Recent */}
      <section className="mt-10">
        <h2 className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Recently redeemed</h2>
        <Card className="mt-3 overflow-hidden">
          {loadingRecent ? (
            <div className="space-y-2 p-4">
              <Skeleton className="h-10" /><Skeleton className="h-10" /><Skeleton className="h-10" />
            </div>
          ) : recent.length === 0 ? (
            <p className="p-6 text-center text-sm text-muted-foreground">
              No redemptions yet. They'll show up here as customers walk in.
            </p>
          ) : (
            <ul className="divide-y">
              {recent.map((r) => (
                <li key={r.code + r.redeemedAt} className="flex items-center justify-between gap-3 px-4 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{r.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(r.redeemedAt).toLocaleString()}
                    </p>
                  </div>
                  <span className="rounded-md bg-muted px-2 py-1 font-mono text-xs tracking-widest">
                    {r.code}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </section>
    </div>
  );
};

const ResultCard = ({
  result, onConfirm, onReset, busy,
}: {
  result: LookupResult;
  onConfirm: (amountCents: number) => void;
  onReset: () => void;
  busy: boolean;
}) => {
  const claimedAgo = useMemo(() => {
    if (result.kind !== "ok" && result.kind !== "already") return null;
    const ms = Date.now() - new Date(result.claim.claimed_at).getTime();
    const min = Math.round(ms / 60000);
    if (min < 1) return "just now";
    if (min < 60) return `${min} min ago`;
    const h = Math.round(min / 60);
    return `${h} h ago`;
  }, [result]);

  // Order amount entry — kept hook-side so it stays mounted while we type.
  const [amount, setAmount] = useState("");
  const [amountError, setAmountError] = useState<string | null>(null);
  const amountRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (result.kind === "ok") {
      setAmount("");
      setAmountError(null);
      // Autofocus so the merchant can start typing the amount immediately.
      setTimeout(() => amountRef.current?.focus(), 50);
    }
  }, [result.kind, result.kind === "ok" ? result.claim.id : null]);

  const submitAmount = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (result.kind !== "ok") return;
    // Accept "12,50" or "12.50". Strip everything else.
    const normalized = amount.trim().replace(",", ".");
    const num = Number(normalized);
    if (!normalized || !Number.isFinite(num) || num <= 0) {
      setAmountError("Enter the order total in euros, e.g. 12.50");
      amountRef.current?.focus();
      return;
    }
    if (num > 100000) {
      setAmountError("That looks too high — double-check.");
      return;
    }
    const cents = Math.round(num * 100);
    onConfirm(cents);
  };

  if (result.kind === "not_found") {
    return (
      <Banner tone="error" icon={XCircle} title="Code not found">
        Double-check the four characters with the customer. The code shown to them looks like
        <span className="mx-1 rounded bg-background px-1.5 py-0.5 font-mono">SPARK-A4F2</span>.
        <div className="mt-3"><Button variant="outline" size="sm" onClick={onReset}><RotateCcw className="h-3.5 w-3.5" /> Try again</Button></div>
      </Banner>
    );
  }
  if (result.kind === "wrong_business") {
    return (
      <Banner tone="error" icon={XCircle} title="That code isn't for your business">
        It belongs to another merchant. Ask the customer to re-open their wallet.
        <div className="mt-3"><Button variant="outline" size="sm" onClick={onReset}><RotateCcw className="h-3.5 w-3.5" /> Try again</Button></div>
      </Banner>
    );
  }
  if (result.kind === "error") {
    return (
      <Banner tone="error" icon={AlertCircle} title="Something went wrong">
        {result.message}
      </Banner>
    );
  }
  if (result.kind === "already") {
    return (
      <Banner tone="warning" icon={AlertCircle} title="Already redeemed">
        <p className="text-sm font-medium text-foreground">{result.offer.title}</p>
        <p className="mt-1 text-xs">
          Redeemed {result.claim.redeemed_at ? new Date(result.claim.redeemed_at).toLocaleString() : "earlier"}.
        </p>
        <div className="mt-3"><Button variant="outline" size="sm" onClick={onReset}>Done</Button></div>
      </Banner>
    );
  }
  if (result.kind === "demo_redeemed") {
    return (
      <Banner tone="success" icon={CheckCircle2} title="Redeemed">
        <p className="font-display text-lg font-semibold text-foreground">Cold drink on us — 10% off</p>
        <p className="mt-0.5 text-sm font-medium text-primary">–10% any cold drink</p>
        <div className="mt-3 flex items-center gap-2">
          <span className="rounded-md bg-background px-2 py-0.5 font-mono tracking-widest text-xs">{result.code}</span>
          <Button variant="outline" size="sm" onClick={onReset}>Done</Button>
        </div>
      </Banner>
    );
  }

  // OK — ready to redeem; collect the order amount before confirming.
  return (
    <Banner tone="success" icon={CheckCircle2} title="Valid code">
      <p className="font-display text-lg font-semibold text-foreground">{result.offer.title}</p>
      {result.offer.discount_label && (
        <p className="mt-0.5 text-sm font-medium text-primary">{result.offer.discount_label}</p>
      )}
      <p className="mt-1 text-sm text-muted-foreground">{result.offer.description}</p>
      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> Claimed {claimedAgo}</span>
        {result.offer.end_time && (
          <span className="rounded-full bg-background px-2 py-0.5 font-mono">Valid until {result.offer.end_time.slice(0, 5)}</span>
        )}
        <span className="rounded-md bg-background px-2 py-0.5 font-mono tracking-widest">{result.claim.code}</span>
      </div>

      <form onSubmit={submitAmount} className="mt-4 space-y-2">
        <label htmlFor="redeem-amount" className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Order total
        </label>
        <div className="flex flex-col items-stretch gap-2 sm:flex-row">
          <div className="relative w-full sm:flex-1">
            <Euro className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="redeem-amount"
              ref={amountRef}
              value={amount}
              onChange={(e) => {
                setAmountError(null);
                // Allow digits + one decimal separator only.
                const v = e.target.value.replace(/[^0-9.,]/g, "");
                setAmount(v);
              }}
              placeholder="12.50"
              inputMode="decimal"
              autoComplete="off"
              maxLength={8}
              aria-invalid={!!amountError}
              className="h-12 w-full pl-9 font-mono text-lg"
            />
          </div>
          <Button type="submit" disabled={busy || !amount.trim()} className="h-12 w-full sm:w-auto sm:min-w-40">
            {busy ? "Saving…" : "Mark as redeemed"}
          </Button>
        </div>
        {amountError && (
          <p className="flex items-center gap-1.5 text-xs text-destructive">
            <AlertCircle className="h-3.5 w-3.5" /> {amountError}
          </p>
        )}
        <p className="text-[11px] text-muted-foreground">
          Used to track how much revenue Spark brings in. Stays private to your business.
        </p>
        <div>
          <Button type="button" variant="ghost" size="sm" onClick={onReset} disabled={busy}>Cancel</Button>
        </div>
      </form>
    </Banner>
  );
};

const TONE: Record<string, string> = {
  success: "border-primary/30 bg-primary/5",
  warning: "border-amber-400/40 bg-amber-50",
  error: "border-destructive/30 bg-destructive/5",
};
const ICON_TONE: Record<string, string> = {
  success: "text-primary",
  warning: "text-amber-600",
  error: "text-destructive",
};

const Banner = ({
  tone, icon: Icon, title, children,
}: {
  tone: "success" | "warning" | "error";
  icon: React.ElementType;
  title: string;
  children: React.ReactNode;
}) => (
  <div className={`flex items-start gap-3 rounded-xl border p-4 ${TONE[tone]}`}>
    <div className="mt-0.5"><Icon className={`h-5 w-5 ${ICON_TONE[tone]}`} /></div>
    <div className="min-w-0 flex-1 text-sm text-muted-foreground">
      <p className={`font-display text-base font-semibold ${ICON_TONE[tone]}`}>{title}</p>
      <div className="mt-1">{children}</div>
    </div>
  </div>
);

export default Redeem;
