import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "@/hooks/use-toast";
import { Sparkles, Store, User, Zap } from "lucide-react";

// Shared demo credentials — auto-provisioned on first click.
const DEMO_ACCOUNTS = {
  customer: { email: "demo.customer@spark.test", password: "spark-demo-1234", full_name: "Demo Customer" },
  business: { email: "demo.business@spark.test", password: "spark-demo-1234", full_name: "Demo Café Owner" },
} as const;

const emailSchema = z.string().trim().email().max(255);
const passwordSchema = z.string().min(6).max(72);
const nameSchema = z.string().trim().min(1).max(100);

// Access key required to register a business account. Frontend-only gate
// (the demo doesn't ship with a backend role-approval flow).
const BUSINESS_ACCESS_KEY = "SPARK-BIZ-2026";

const Auth = () => {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { user, role, loading } = useAuth();

  const [mode, setMode] = useState<"signin" | "signup">(params.get("mode") === "signup" ? "signup" : "signin");
  const [chosenRole, setChosenRole] = useState<"customer" | "business">(
    (params.get("role") as "business" | "customer") ?? "business",
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [accessKey, setAccessKey] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user && role) {
      if (role === "business") navigate("/dashboard", { replace: true });
      else navigate("/wallet", { replace: true });
    }
  }, [user, role, loading, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const e1 = emailSchema.safeParse(email);
      const p1 = passwordSchema.safeParse(password);
      if (!e1.success) throw new Error("Enter a valid email");
      if (!p1.success) throw new Error("Password must be at least 6 characters");

      if (mode === "signup") {
        const n1 = nameSchema.safeParse(fullName);
        if (!n1.success) throw new Error("Enter your name");
        if (chosenRole === "business" && accessKey.trim() !== BUSINESS_ACCESS_KEY) {
          throw new Error("Invalid business access key");
        }
        const { error } = await supabase.auth.signUp({
          email, password,
          options: {
            emailRedirectTo: `${window.location.origin}/`,
            data: { full_name: fullName, role: chosenRole },
          },
        });
        if (error) throw error;
        toast({ title: "Welcome to Spark", description: "Account created." });
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Something went wrong";
      toast({ title: "Authentication error", description: msg, variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  // One-click demo login. Tries to sign in; if the account doesn't exist yet,
  // sign up (auto-confirm is enabled for demo) then sign in.
  const handleDemoLogin = async (which: "customer" | "business") => {
    setSubmitting(true);
    try {
      const acc = DEMO_ACCOUNTS[which];
      const { error: signInErr } = await supabase.auth.signInWithPassword({
        email: acc.email,
        password: acc.password,
      });
      if (signInErr) {
        const { error: signUpErr } = await supabase.auth.signUp({
          email: acc.email,
          password: acc.password,
          options: {
            emailRedirectTo: `${window.location.origin}/`,
            data: { full_name: acc.full_name, role: which },
          },
        });
        if (signUpErr) throw signUpErr;
        const { error: retryErr } = await supabase.auth.signInWithPassword({
          email: acc.email,
          password: acc.password,
        });
        if (retryErr) throw retryErr;
      }
      // For business demo, ensure an onboarded business exists so the user
      // skips the onboarding flow and lands directly on the dashboard.
      if (which === "business") {
        const { data: sessionData } = await supabase.auth.getUser();
        const uid = sessionData.user?.id;
        if (uid) {
          // Use limit(1) instead of maybeSingle() — the demo account may already
          // own multiple businesses from prior sessions, which would make
          // maybeSingle() error and trigger another redundant insert.
          const { data: existingRows } = await supabase
            .from("businesses")
            .select("id, onboarding_completed")
            .eq("owner_id", uid)
            .limit(1);
          const existing = existingRows?.[0];
          if (!existing) {
            const { data: created } = await supabase
              .from("businesses")
              .insert({
                owner_id: uid,
                name: "Demo Café Spark",
                category: "Café",
                address: "Königstraße 1",
                city: "Stuttgart",
                country: "DE",
                latitude: 48.7784,
                longitude: 9.1800,
                onboarding_completed: true,
              })
              .select("id")
              .maybeSingle();
            if (created?.id) {
              await supabase.rpc("seed_payone_mock", { _business_id: created.id });
            }
          } else if (!existing.onboarding_completed) {
            await supabase
              .from("businesses")
              .update({ onboarding_completed: true })
              .eq("id", existing.id);
          }
        }
      }
      toast({ title: "Demo mode", description: `Signed in as test ${which}.` });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Couldn't start demo";
      toast({ title: "Demo error", description: msg, variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Left brand panel */}
      <div className="relative hidden bg-primary text-primary-foreground lg:flex">
        <div className="absolute inset-0" style={{ background: "var(--gradient-primary)" }} />
        <div className="relative z-10 flex flex-col justify-between p-12">
          <Link to="/" className="flex items-center gap-2">
            <div className="grid h-8 w-8 place-items-center rounded-md bg-primary-foreground/15 backdrop-blur">
              <Sparkles className="h-4 w-4" />
            </div>
            <span className="text-lg font-semibold">Spark</span>
          </Link>
          <div>
            <h2 className="text-4xl font-semibold leading-tight">
              Fill your quiet hours.<br />Reward the right moment.
            </h2>
            <p className="mt-4 max-w-md text-primary-foreground/85">
              Join Spark and turn local context into customers walking through your door.
            </p>
          </div>
          <p className="text-xs text-primary-foreground/70">Powered by DSV-Gruppe · Sparkassen-Finanzgruppe</p>
        </div>
      </div>

      {/* Right form */}
      <div className="flex items-center justify-center p-6 sm:p-10">
        <Card className="w-full max-w-md border-0 shadow-none sm:border sm:shadow-[var(--shadow-card)]">
          <CardHeader>
            <CardTitle className="text-2xl">{mode === "signup" ? "Create your account" : "Welcome back"}</CardTitle>
            <CardDescription>
              {mode === "signup" ? "Get started in under a minute." : "Sign in to continue to Spark."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* Demo mode — one-click access for reviewers */}
            <div className="rounded-lg border border-dashed bg-muted/40 p-3">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <Zap className="h-3.5 w-3.5" />
                Try the demo — no signup needed
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={submitting}
                  onClick={() => handleDemoLogin("customer")}
                  className="justify-start"
                >
                  <User className="h-4 w-4" />
                  As Customer
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={submitting}
                  onClick={() => handleDemoLogin("business")}
                  className="justify-start"
                >
                  <Store className="h-4 w-4" />
                  As Business
                </Button>
              </div>
            </div>

            <div className="relative">
              <div className="absolute inset-0 flex items-center"><span className="w-full border-t" /></div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-card px-2 text-muted-foreground">or</span>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === "signup" && (
                <>
                  <div className="grid grid-cols-2 gap-2 rounded-lg border p-1">
                    {(["business", "customer"] as const).map((r) => {
                      const Icon = r === "business" ? Store : User;
                      return (
                        <button
                          key={r}
                          type="button"
                          onClick={() => setChosenRole(r)}
                          className={`flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                            chosenRole === r ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"
                          }`}
                        >
                          <Icon className="h-4 w-4" />
                          {r === "business" ? "Business" : "Customer"}
                        </button>
                      );
                    })}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="name">{chosenRole === "business" ? "Your name" : "Full name"}</Label>
                    <Input id="name" value={fullName} onChange={(e) => setFullName(e.target.value)} maxLength={100} required />
                  </div>
                  {chosenRole === "business" && (
                    <div className="space-y-2">
                      <Label htmlFor="access-key">Business access key</Label>
                      <Input
                        id="access-key"
                        value={accessKey}
                        onChange={(e) => setAccessKey(e.target.value)}
                        placeholder="Enter your invite key"
                        maxLength={64}
                        required
                      />
                      <p className="text-xs text-muted-foreground">
                        Required to register a merchant account. Contact Spark for an invite.
                      </p>
                    </div>
                  )}
                </>
              )}
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} maxLength={255} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={6} maxLength={72} required />
              </div>
              <Button type="submit" className="w-full" size="lg" disabled={submitting}>
                {submitting ? "Please wait…" : mode === "signup" ? "Create account" : "Sign in"}
              </Button>
              <p className="text-center text-sm text-muted-foreground">
                {mode === "signup" ? (
                  <>Already have an account?{" "}
                    <button type="button" className="font-medium text-primary hover:underline" onClick={() => setMode("signin")}>Sign in</button>
                  </>
                ) : (
                  <>New to Spark?{" "}
                    <button type="button" className="font-medium text-primary hover:underline" onClick={() => setMode("signup")}>Create an account</button>
                  </>
                )}
              </p>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Auth;
