import React, { useEffect, lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AppProvider, useApp } from "@/contexts/AppContext";
import Layout from "@/components/Layout";
import ErrorBoundary from "@/components/ErrorBoundary";
import ScrollToTop from "@/components/ScrollToTop";

// PERF: code-split every route into its own chunk (loaded on demand).
const Auth = lazy(() => import("@/pages/Auth"));
const Onboarding = lazy(() => import("@/pages/Onboarding"));
const Candidates = lazy(() => import("@/pages/Candidates"));
const ProfileDetail = lazy(() => import("@/pages/ProfileDetail"));
const Messages = lazy(() => import("@/pages/Messages"));
const Chat = lazy(() => import("@/pages/Chat"));
const Saved = lazy(() => import("@/pages/Saved"));
const Me = lazy(() => import("@/pages/Me"));
const Premium = lazy(() => import("@/pages/Premium"));
const Admin = lazy(() => import("@/pages/Admin"));
const Settings = lazy(() => import("@/pages/Settings"));
const Notifications = lazy(() => import("@/pages/Notifications"));
const Quiz = lazy(() => import("@/pages/Quiz"));
const Boost = lazy(() => import("@/pages/Boost"));
const Personality = lazy(() => import("@/pages/Personality"));
const Chaperone = lazy(() => import("@/pages/Chaperone"));
const ChaperoneWard = lazy(() => import("@/pages/ChaperoneWard"));
const Prompts = lazy(() => import("@/pages/Prompts"));
const Stories = lazy(() => import("@/pages/Stories"));
const Withdrawals = lazy(() => import("@/pages/Withdrawals"));
const Family = lazy(() => import("@/pages/Family"));
const Concierge = lazy(() => import("@/pages/Concierge"));
const Travel = lazy(() => import("@/pages/Travel"));
const Verification = lazy(() => import("@/pages/Verification"));
const Welcome = lazy(() => import("@/pages/Welcome"));
const About = lazy(() => import("@/pages/About"));
const FAQ = lazy(() => import("@/pages/FAQ"));
const Referral = lazy(() => import("@/pages/Referral"));
const Swipe = lazy(() => import("@/pages/Swipe"));

function PageSpinner() {
  return (
    <div className="min-h-[50vh] grid place-items-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
        <p className="text-xs text-muted-foreground">Yuklanmoqda...</p>
      </div>
    </div>
  );
}

function Gate({ children }) {
  const { user, loading } = useApp();
  const location = useLocation();
  if (loading) return <div className="min-h-screen grid place-items-center text-muted-foreground">Loading...</div>;
  if (!user) return <Navigate to="/auth" replace state={{ from: location }} />;
  if (!user.onboarded && location.pathname !== "/onboarding") return <Navigate to="/onboarding" replace />;
  return children;
}

function Inner() {
  // Inject Telegram WebApp script at runtime; init expand & viewport
  useEffect(() => {
    const init = () => {
      const tg = window.Telegram?.WebApp;
      if (!tg) return;
      try {
        tg.ready();
        tg.expand();
        if (tg.setHeaderColor) tg.setHeaderColor("#ffffff");
        if (tg.setBackgroundColor) tg.setBackgroundColor("#ffffff");
        if (tg.enableClosingConfirmation) tg.enableClosingConfirmation();
      } catch (e) { /* ignore */ }
    };
    if (window.Telegram?.WebApp) { init(); return; }
    const s = document.createElement("script");
    s.src = "https://telegram.org/js/telegram-web-app.js";
    s.async = true;
    s.onload = init;
    document.head.appendChild(s);
  }, []);

  return (
    <Suspense fallback={<PageSpinner />}>
      <Routes>
        <Route path="/welcome" element={<Welcome />} />
        <Route path="/about" element={<About />} />
        <Route path="/faq" element={<FAQ />} />
        <Route path="/auth" element={<Auth />} />
        <Route path="/onboarding" element={<Gate><Onboarding /></Gate>} />
        <Route element={<Gate><Layout /></Gate>}>
          <Route index element={<Candidates />} />
          <Route path="/candidate/:id" element={<ProfileDetail />} />
          <Route path="/messages" element={<Messages />} />
          <Route path="/chat/:otherId" element={<Chat />} />
          <Route path="/saved" element={<Saved />} />
          <Route path="/me" element={<Me />} />
          <Route path="/premium" element={<Premium />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/quiz" element={<Quiz />} />
          <Route path="/personality" element={<Personality />} />
          <Route path="/chaperone" element={<Chaperone />} />
          <Route path="/chaperone/ward/:wardId" element={<ChaperoneWard />} />
          <Route path="/prompts" element={<Prompts />} />
          <Route path="/stories" element={<Stories />} />
          <Route path="/withdrawals" element={<Withdrawals />} />
          <Route path="/family" element={<Family />} />
          <Route path="/concierge" element={<Concierge />} />
          <Route path="/travel" element={<Travel />} />
          <Route path="/verification" element={<Verification />} />
          <Route path="/boost" element={<Boost />} />
          <Route path="/referral" element={<Referral />} />
          <Route path="/swipe" element={<Swipe />} />
          <Route path="/admin" element={<Admin />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AppProvider>
        <BrowserRouter>
          <ScrollToTop />
          <Toaster position="top-center" richColors />
          <Inner />
        </BrowserRouter>
      </AppProvider>
    </ErrorBoundary>
  );
}
