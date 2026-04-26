import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/hooks/useAuth";
import { RequireAuth } from "@/components/RequireAuth";
import Index from "./pages/Index.tsx";
import Auth from "./pages/Auth.tsx";
import Onboarding from "./pages/business/Onboarding.tsx";
import Dashboard from "./pages/business/Dashboard.tsx";
import WalletShell from "./pages/customer/WalletShell.tsx";
import NotFound from "./pages/NotFound.tsx";
import { InstallPrompt } from "@/components/InstallPrompt";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <InstallPrompt />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="/auth" element={<Auth />} />
            <Route path="/onboarding" element={<RequireAuth role="business"><Onboarding /></RequireAuth>} />
            <Route path="/dashboard/*" element={<RequireAuth role="business"><Dashboard /></RequireAuth>} />
            <Route path="/wallet/*" element={<RequireAuth role="customer"><WalletShell /></RequireAuth>} />
            {/* Legacy redirect */}
            <Route path="/customer" element={<Navigate to="/wallet" replace />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
