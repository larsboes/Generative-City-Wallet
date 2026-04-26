import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { Sparkles, Compass, Map as MapIcon, CalendarDays, Bookmark, User } from "lucide-react";
import Now from "./Now";
import Saved from "./Saved";
import Me from "./Me";
import OfferDetail from "./OfferDetail";
import MapView from "./MapView";
import Calendar from "./Calendar";
import SparkLanding from "./SparkLanding";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";

const tabs = [
  { to: "/wallet", icon: Compass, label: "Now", end: true },
  { to: "/wallet/map", icon: MapIcon, label: "Map" },
  { to: "/wallet/calendar", icon: CalendarDays, label: "Day" },
  { to: "/wallet/saved", icon: Bookmark, label: "Saved" },
  { to: "/wallet/me", icon: User, label: "Me" },
];

const WalletShell = () => {
  const { user } = useAuth();

  // Ensure customer prefs row exists
  useEffect(() => {
    if (!user) return;
    supabase.from("customer_prefs").select("user_id").eq("user_id", user.id).maybeSingle()
      .then(({ data }) => {
        if (!data) {
          supabase.from("customer_prefs").insert({ user_id: user.id }).then(() => {});
        }
      });
  }, [user]);

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Now />} />
        <Route path="map" element={<MapView />} />
        <Route path="calendar" element={<Calendar />} />
        <Route path="saved" element={<Saved />} />
        <Route path="me" element={<Me />} />
      </Route>
      <Route path="offer/:id" element={<OfferDetail />} />
      <Route path="spark/:code" element={<SparkLanding />} />
      <Route path="*" element={<Navigate to="/wallet" replace />} />
    </Routes>
  );
};

const Layout = () => (
  <div className="min-h-screen bg-background grain">
    {/* Mobile-first centered shell */}
    <div className="mx-auto flex min-h-screen w-full max-w-md flex-col bg-background pb-[calc(5rem+env(safe-area-inset-bottom))] md:max-w-lg md:border-x md:border-border/60">
      {/* Top brand bar */}
      <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-border/60 bg-background/85 px-4 backdrop-blur-md sm:px-5">
        <Link to="/wallet" className="flex items-center gap-2">
          <div className="grid h-7 w-7 place-items-center rounded-md bg-primary text-primary-foreground shadow-[var(--shadow-elegant)]">
            <Sparkles className="h-3.5 w-3.5" />
          </div>
          <span className="font-display text-lg font-semibold">Spark</span>
        </Link>
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Wallet</span>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      {/* Bottom nav */}
      <nav className="fixed bottom-0 left-1/2 z-50 w-full max-w-md -translate-x-1/2 border-t border-border/60 bg-background/95 pb-safe backdrop-blur-md md:max-w-lg">
        <ul className="flex">
          {tabs.map(({ to, icon: Icon, label, end }) => (
            <li key={to} className="flex-1">
              <NavLink
                to={to}
                end={end}
                className={({ isActive }) =>
                  `relative flex flex-col items-center gap-1 py-2.5 text-[10px] font-medium transition-colors sm:py-3 sm:text-[11px] ${
                    isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && <span className="absolute top-0 h-0.5 w-8 rounded-b-full bg-primary" />}
                    <Icon className="h-5 w-5" strokeWidth={isActive ? 2.25 : 1.75} />
                    {label}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  </div>
);

export default WalletShell;
