import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  MapPin,
  Sparkles,
  Users,
  Coffee,
  Briefcase,
  UtensilsCrossed,
  Loader2,
  ArrowUpRight,
  Star,
} from "lucide-react";
import { format } from "date-fns";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { useGeolocation } from "@/hooks/useGeolocation";

type EventType = "coffee" | "lunch" | "meeting" | "interview" | "happy_hour";

interface MockEvent {
  id: string;
  title: string;
  type: EventType;
  start: string; // "HH:MM"
  end: string;
  attendees: number;
  notes?: string;
  location?: string; // already booked
}

interface VenuePick {
  id: string;
  name: string;
  category: string | null;
  city: string | null;
  address: string | null;
  rating: number | null;
  price_level: number | null;
  offer_title?: string | null;
  offer_discount?: string | null;
  reason: string;
}

const TYPE_META: Record<
  EventType,
  { label: string; icon: typeof Coffee }
> = {
  coffee: { label: "Coffee", icon: Coffee },
  lunch: { label: "Lunch", icon: UtensilsCrossed },
  meeting: { label: "Meetup", icon: Users },
  interview: { label: "Interview", icon: Briefcase },
  happy_hour: { label: "Drinks", icon: Sparkles },
};

const MOCK_EVENTS: MockEvent[] = [
  {
    id: "e3",
    title: "Lunch with Marco",
    type: "lunch",
    start: "14:00",
    end: "15:00",
    attendees: 2,
    notes: "Want something quick, not too heavy.",
  },
  {
    id: "e4",
    title: "1:1 with Lisa",
    type: "meeting",
    start: "15:00",
    end: "16:00",
    attendees: 2,
    location: "Room 50.203",
  },
  {
    id: "e5",
    title: "Win hackathon",
    type: "meeting",
    start: "16:30",
    end: "18:30",
    attendees: 4,
    location: "Start2Grow Munich",
  },
  {
    id: "e6",
    title: "Party",
    type: "happy_hour",
    start: "19:00",
    end: "23:00",
    attendees: 8,
    location: "Online",
  },
];

const toMinutes = (hhmm: string) => {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
};

const formatDuration = (start: string, end: string) => {
  const mins = toMinutes(end) - toMinutes(start);
  if (mins < 60) return `${mins}m`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m === 0 ? `${h}h` : `${h}h${m}m`;
};

const Calendar = () => {
  const today = useMemo(() => new Date(), []);
  const geo = useGeolocation();
  const [openEventId, setOpenEventId] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [picksByEvent, setPicksByEvent] = useState<
    Record<string, { picks: VenuePick[]; summary: string }>
  >({});

  const nowMin = today.getHours() * 60 + today.getMinutes();
  const nextEventId = "e3";

  const eventsNeedingVenue = MOCK_EVENTS.filter((e) => !e.location).length;

  const requestSuggestions = async (event: MockEvent) => {
    setLoadingId(event.id);
    setOpenEventId(event.id);
    try {
      // Deterministic pick for the lunch — always recommend L'Osteria Welfenstraße.
      if (event.id === "e3") {
        const { data: biz } = await supabase
          .from("businesses")
          .select("id, name, category, address, city, rating, price_level")
          .ilike("name", "L'Osteria München Welfenstraße")
          .maybeSingle();
        if (biz) {
          setPicksByEvent((m) => ({
            ...m,
            [event.id]: {
              picks: [
                {
                  id: biz.id,
                  name: biz.name,
                  category: biz.category,
                  city: biz.city,
                  address: biz.address,
                  rating: biz.rating,
                  price_level: biz.price_level,
                  offer_title: "2-for-1 Aperitivi",
                  offer_discount: "2 for 1",
                  reason:
                    "Lively Italian spot a short walk away — grab a quick bite and start lunch with a 2-for-1 aperitivo on the house.",
                },
              ],
              summary:
                "L'Osteria Welfenstraße is the easy call: fast Italian, group-friendly tables, and a 2-for-1 aperitivo to kick things off.",
            },
          }));
          setLoadingId(null);
          return;
        }
      }

      const { data: offers } = await supabase
        .from("offers")
        .select("id, business_id, title, discount_label")
        .eq("status", "active")
        .limit(40);

      const ids = Array.from(new Set((offers ?? []).map((o) => o.business_id)));
      let venues: any[] = [];
      if (ids.length) {
        const { data } = await supabase
          .from("businesses")
          .select("id, name, category, address, city, rating, price_level")
          .in("id", ids);
        venues = data ?? [];
      }
      const offerByBiz = new Map<
        string,
        { title: string; discount_label: string | null }
      >();
      (offers ?? []).forEach((o) => {
        if (!offerByBiz.has(o.business_id))
          offerByBiz.set(o.business_id, {
            title: o.title,
            discount_label: o.discount_label,
          });
      });

      const candidates = venues.map((v) => ({
        id: v.id,
        name: v.name,
        category: v.category,
        address: v.address,
        city: v.city,
        rating: v.rating,
        price_level: v.price_level,
        offer_title: offerByBiz.get(v.id)?.title ?? null,
        offer_discount: offerByBiz.get(v.id)?.discount_label ?? null,
      }));

      if (candidates.length === 0) {
        toast.info(
          "No nearby venues with active offers yet — try again once merchants drop more.",
        );
        setLoadingId(null);
        return;
      }

      const { data, error } = await supabase.functions.invoke(
        "suggest-event-venue",
        {
          body: {
            event: {
              title: event.title,
              type: TYPE_META[event.type].label,
              start: event.start,
              end: event.end,
              notes: event.notes,
              attendees: event.attendees,
            },
            candidates,
            city: geo.resolvedCity?.supported,
          },
        },
      );

      if (error) {
        toast.error(error.message ?? "Could not get a suggestion");
        return;
      }
      setPicksByEvent((m) => ({
        ...m,
        [event.id]: { picks: data.picks ?? [], summary: data.summary ?? "" },
      }));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Suggestion failed");
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="pb-12">
      {/* Greeting — matches Now.tsx pattern */}
      <section className="px-5 pb-2 pt-7">
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {format(today, "EEEE")} · Today
        </p>
        <h1 className="mt-2 font-display text-3xl font-semibold leading-tight text-balance">
          {format(today, "MMMM d")}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {eventsNeedingVenue > 0 ? (
            <>
              {eventsNeedingVenue} of your {MOCK_EVENTS.length} events still
              need a spot. Tap{" "}
              <span className="font-medium text-foreground">Find a spot</span>{" "}
              and Spark will pick.
            </>
          ) : (
            <>You're all booked in. Spark is on standby.</>
          )}
        </p>
      </section>

      {/* Day strip */}
      <section className="px-5 pt-5">
        <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Schedule
        </p>
        <ul className="space-y-2.5">
          {MOCK_EVENTS.map((ev) => {
            const meta = TYPE_META[ev.type];
            const Icon = meta.icon;
            const isOpen = openEventId === ev.id;
            const result = picksByEvent[ev.id];
            const isLoading = loadingId === ev.id;
            const canSuggest = !ev.location;
            const isNext = ev.id === nextEventId;

            return (
              <li
                key={ev.id}
                className="overflow-hidden rounded-xl border bg-card shadow-sm transition-shadow hover:shadow-[var(--shadow-card)]"
              >
                <div className="flex gap-3 p-3">
                  {/* Time block — mirrors RowOfferCard photo block */}
                  <div className="flex h-20 w-20 shrink-0 flex-col items-center justify-center rounded-lg bg-muted">
                    <span className="font-display text-lg font-semibold leading-none">
                      {ev.start}
                    </span>
                    <span className="mt-1.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                      {formatDuration(ev.start, ev.end)}
                    </span>
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      {isNext ? (
                        <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-primary">
                          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
                          Up next
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                          <Icon className="h-3 w-3" />
                          {meta.label}
                        </span>
                      )}
                      <span className="text-[10px] text-muted-foreground">
                        · {ev.end}
                      </span>
                      <span className="ml-auto flex items-center gap-1 text-[10px] text-muted-foreground">
                        <Users className="h-3 w-3" />
                        {ev.attendees}
                      </span>
                    </div>

                    <p className="mt-1 line-clamp-2 font-display text-base font-semibold leading-snug">
                      {ev.title}
                    </p>

                    <div className="mt-2 flex items-center justify-between gap-2">
                      {ev.location ? (
                        <span className="flex min-w-0 items-center gap-1 text-xs text-muted-foreground">
                          <MapPin className="h-3.5 w-3.5 shrink-0" />
                          <span className="truncate">{ev.location}</span>
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          No venue yet
                        </span>
                      )}

                      {canSuggest && (
                        <Button
                          size="sm"
                          variant={result ? "outline" : "default"}
                          className="h-7 gap-1.5 px-2.5 text-[11px]"
                          onClick={() =>
                            isOpen && result
                              ? setOpenEventId(null)
                              : requestSuggestions(ev)
                          }
                          disabled={isLoading}
                        >
                          {isLoading ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Sparkles className="h-3 w-3" />
                          )}
                          {result
                            ? isOpen
                              ? "Hide picks"
                              : "View picks"
                            : "Find a spot"}
                        </Button>
                      )}
                    </div>
                  </div>
                </div>

                {isOpen && (
                  <div className="border-t bg-muted/30 px-3 pb-3 pt-3">
                    {isLoading && (
                      <div className="space-y-2">
                        <Skeleton className="h-4 w-2/3" />
                        <Skeleton className="h-16 w-full rounded-lg" />
                        <Skeleton className="h-16 w-full rounded-lg" />
                      </div>
                    )}
                    {!isLoading && result && (
                      <>
                        {result.summary && (
                          <p className="mb-3 flex items-start gap-2 rounded-lg border border-primary/20 bg-primary/5 p-2.5 text-xs leading-relaxed text-foreground">
                            <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                            <span>{result.summary}</span>
                          </p>
                        )}
                        {result.picks.length === 0 ? (
                          <p className="rounded-lg border border-dashed p-3 text-center text-xs text-muted-foreground">
                            No good match nearby right now.
                          </p>
                        ) : (
                          <ul className="space-y-2">
                            {result.picks.map((p, i) => (
                              <li
                                key={p.id}
                                className="flex gap-3 rounded-lg border bg-card p-3 shadow-sm"
                              >
                                <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-primary/10 font-display text-sm font-semibold text-primary">
                                  {i + 1}
                                </div>
                                <div className="min-w-0 flex-1">
                                  <p className="truncate font-display text-sm font-semibold">
                                    {p.name}
                                  </p>
                                  <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-[11px] text-muted-foreground">
                                    {p.category && <span>{p.category}</span>}
                                    {p.category && p.rating != null && (
                                      <span>·</span>
                                    )}
                                    {p.rating != null && (
                                      <span className="inline-flex items-center gap-0.5">
                                        <Star className="h-3 w-3 fill-current" />
                                        {p.rating.toFixed(1)}
                                      </span>
                                    )}
                                  </p>
                                  <p className="mt-1.5 text-xs leading-relaxed text-foreground/90">
                                    {p.reason}
                                  </p>
                                  {p.offer_title && (
                                    <span className="mt-2 inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-primary">
                                      <Sparkles className="h-3 w-3" />
                                      {p.offer_discount ?? p.offer_title}
                                    </span>
                                  )}
                                </div>
                                <Link
                                  to={`/wallet/map?business=${p.id}`}
                                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition hover:opacity-90"
                                  title="Open in map"
                                >
                                  <ArrowUpRight className="h-4 w-4" />
                                </Link>
                              </li>
                            ))}
                          </ul>
                        )}
                      </>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </section>

      <div className="px-5 pt-12 pb-6 text-center text-[11px] text-muted-foreground">
        Schedule is mocked — calendar sync coming soon.
      </div>
    </div>
  );
};

export default Calendar;
