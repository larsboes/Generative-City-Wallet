import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Sparkles, LayoutDashboard, Tag, Settings as SettingsIcon, LogOut, MapPin, Menu, X, ScanLine, Bell,
} from "lucide-react";
import Offers from "./Offers";
import Overview from "./Overview";
import Redeem from "./Redeem";
import Notifications from "./Notifications";

interface Business {
  id: string;
  name: string;
  category: string | null;
  address: string | null;
  city: string | null;
  photo_url: string | null;
  rating: number | null;
  website: string | null;
  phone: string | null;
  onboarding_completed: boolean;
}

const useBusiness = () => {
  const { user } = useAuth();
  const [business, setBusiness] = useState<Business | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!user) {
      setBusiness(null);
      setLoading(true);
      return;
    }
    let cancelled = false;
    setLoading(true);
    supabase
      .rpc("get_my_business")
      .then(({ data }) => {
        if (cancelled) return;
        const rows = (data as Business[] | null) ?? [];
        // Prefer the onboarded row, then earliest created.
        const sorted = [...rows].sort((a: any, b: any) => {
          if (a.onboarding_completed !== b.onboarding_completed) {
            return a.onboarding_completed ? -1 : 1;
          }
          return 0;
        });
        setBusiness(sorted[0] ?? null);
        setLoading(false);
      });
    return () => { cancelled = true; };
  }, [user]);
  return { business, loading };
};

const navItems = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Overview", end: true },
  { to: "/dashboard/offers", icon: Tag, label: "Offers" },
  { to: "/dashboard/redeem", icon: ScanLine, label: "Redeem" },
  { to: "/dashboard/notifications", icon: Bell, label: "Notifications" },
  { to: "/dashboard/settings", icon: SettingsIcon, label: "Settings" },
];

const Dashboard = () => {
  const { business, loading } = useBusiness();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!loading && (!business || !business.onboarding_completed)) {
      navigate("/onboarding", { replace: true });
    }
  }, [loading, business, navigate]);

  if (loading || !business) {
    return (
      <div className="grid min-h-screen place-items-center bg-background">
        <div className="flex items-center gap-3 text-muted-foreground">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-primary-foreground">
            <Sparkles className="h-4 w-4" />
          </div>
          <Skeleton className="h-5 w-32" />
        </div>
      </div>
    );
  }

  return (
    <div className="grid min-h-screen md:grid-cols-[260px_1fr]">
      <Sidebar business={business} mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <main className="min-w-0 overflow-x-hidden bg-background">
        <MobileTopBar business={business} onMenu={() => setMobileOpen(true)} />
        <Routes>
          <Route index element={<Overview business={business} />} />
          <Route path="offers" element={<Offers businessId={business.id} />} />
          <Route path="redeem" element={<Redeem businessId={business.id} />} />
          <Route path="notifications" element={<Notifications businessId={business.id} />} />
          <Route path="settings" element={<Settings business={business} />} />
          {/* Legacy routes redirect to overview */}
          <Route path="performance" element={<Navigate to="/dashboard" replace />} />
          <Route path="context" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
};

const Sidebar = ({ business, mobileOpen, onClose }: { business: Business; mobileOpen: boolean; onClose: () => void }) => {
  const { signOut, user } = useAuth();
  const location = useLocation();

  // Close mobile drawer on navigation
  useEffect(() => { onClose(); }, [location.pathname]);

  const initials = business.name
    .split(/\s+/)
    .map((p) => p[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const content = (
    <>
      <div className="flex h-16 items-center justify-between border-b border-sidebar-border px-5">
        <Link to="/dashboard" className="flex items-center gap-2.5">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-primary-foreground shadow-[var(--shadow-elegant)]">
            <Sparkles className="h-4 w-4" />
          </div>
          <span className="font-display text-lg font-semibold text-sidebar-foreground">Spark</span>
        </Link>
        <button className="md:hidden text-sidebar-foreground" onClick={onClose} aria-label="Close menu">
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Business identity card */}
      <div className="border-b border-sidebar-border p-4">
        <div className="flex items-center gap-3">
          {business.photo_url ? (
            <img src={business.photo_url} alt="" className="h-10 w-10 rounded-lg object-cover" />
          ) : (
            <div className="grid h-10 w-10 place-items-center rounded-lg bg-sidebar-accent font-display font-semibold text-sidebar-accent-foreground">
              {initials}
            </div>
          )}
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-sidebar-foreground">{business.name}</p>
            <p className="truncate text-xs text-sidebar-foreground/60">{business.city ?? business.category ?? "Merchant"}</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {navItems.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `relative flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-all ${
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && <span className="absolute inset-y-1.5 left-0 w-0.5 rounded-r-full bg-primary" />}
                <Icon className="h-4 w-4" /> {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <div className="mb-2 px-2 text-xs text-sidebar-foreground/50 truncate">
          {user?.email}
        </div>
        <Button variant="ghost" className="w-full justify-start text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground" onClick={signOut}>
          <LogOut className="h-4 w-4" /> Sign out
        </Button>
      </div>
    </>
  );

  return (
    <>
      {/* Desktop */}
      <aside className="hidden bg-sidebar text-sidebar-foreground md:flex md:flex-col">
        {content}
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <>
          <div className="fixed inset-0 z-40 bg-black/40 md:hidden" onClick={onClose} />
          <aside className="fixed inset-y-0 left-0 z-50 flex w-[260px] flex-col bg-sidebar text-sidebar-foreground md:hidden">
            {content}
          </aside>
        </>
      )}
    </>
  );
};

const MobileTopBar = ({ business, onMenu }: { business: Business; onMenu: () => void }) => (
  <div className="flex h-14 items-center justify-between border-b bg-card px-4 md:hidden">
    <button onClick={onMenu} aria-label="Open menu">
      <Menu className="h-5 w-5" />
    </button>
    <span className="font-display font-semibold">{business.name}</span>
    <div className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-primary-foreground">
      <Sparkles className="h-4 w-4" />
    </div>
  </div>
);

const Settings = ({ business }: { business: Business }) => {
  const navigate = useNavigate();
  return (
    <div className="container max-w-2xl py-10">
      <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Settings</p>
      <h1 className="mt-2 font-display text-4xl font-semibold tracking-tight">Business profile</h1>
      <Card className="mt-8 p-6 shadow-[var(--shadow-card)]">
        <div className="flex items-start gap-4">
          {business.photo_url ? (
            <img src={business.photo_url} alt="" className="h-16 w-16 rounded-xl object-cover" />
          ) : (
            <div className="grid h-16 w-16 place-items-center rounded-xl bg-muted text-muted-foreground">
              <MapPin className="h-5 w-5" />
            </div>
          )}
          <div>
            <h2 className="font-display text-xl font-semibold">{business.name}</h2>
            <p className="text-sm text-muted-foreground">{business.address}</p>
          </div>
        </div>
        <dl className="mt-6 grid gap-4 border-t pt-6 text-sm sm:grid-cols-2">
          <Field label="Category" value={business.category} />
          <Field label="Phone" value={business.phone} />
          <Field label="Website" value={business.website} />
          <Field label="City" value={business.city} />
        </dl>
        <Button variant="outline" className="mt-6" onClick={() => navigate("/onboarding")}>
          Re-run Google Places lookup
        </Button>
      </Card>
    </div>
  );
};

const Field = ({ label, value }: { label: string; value: string | null }) => (
  <div>
    <dt className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">{label}</dt>
    <dd className="mt-1 font-medium">{value ?? "—"}</dd>
  </div>
);

export default Dashboard;
