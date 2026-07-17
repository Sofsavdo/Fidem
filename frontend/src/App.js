import React, { lazy, Suspense, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AppProvider, useApp } from "@/contexts/AppContext";
import Layout from "@/components/Layout";
import ErrorBoundary from "@/components/ErrorBoundary";
import ScrollToTop from "@/components/ScrollToTop";
import BrandSplash from "@/components/BrandSplash";
import { applyTheme, getTheme } from "@/lib/theme";

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
const Personality = lazy(() => import("@/pages/Personality"));
const Prompts = lazy(() => import("@/pages/Prompts"));
const Stories = lazy(() => import("@/pages/Stories"));
const Withdrawals = lazy(() => import("@/pages/Withdrawals"));
const Family = lazy(() => import("@/pages/Family"));
const Concierge = lazy(() => import("@/pages/Concierge"));
const Verification = lazy(() => import("@/pages/Verification"));
const Welcome = lazy(() => import("@/pages/Welcome"));
const About = lazy(() => import("@/pages/About"));
const FAQ = lazy(() => import("@/pages/FAQ"));
const Referral = lazy(() => import("@/pages/Referral"));
const Rankings = lazy(() => import("@/pages/Rankings"));
const Terms = lazy(() => import("@/pages/Terms"));
const Privacy = lazy(() => import("@/pages/Privacy"));
const MeSettings = lazy(() => import("@/pages/MeSettings"));
const PrivacyCenter = lazy(() => import("@/pages/PrivacyCenter"));
const Announcements = lazy(() => import("@/pages/Announcements"));
const GiftShop = lazy(() => import("@/pages/GiftShop"));

function isTelegramWebApp() {
  return Boolean(window.Telegram?.WebApp?.initData);
}

// Both the Telegram auth handoff and route/data loading now show the same
// premium branded splash — no "Telegram orqali kirilmoqda" text, no spinner.
function TelegramLoading() {
  return <BrandSplash full />;
}

function PageSpinner() {
  return <BrandSplash full={false} />;
}

const WELCOMED_KEY = "fidem_welcomed";
function hasSeenWelcome() {
  try { return Boolean(localStorage.getItem(WELCOMED_KEY)); } catch { return false; }
}

function Gate({ children }) {
  const { user, loading } = useApp();
  const location = useLocation();

  if (loading) return <PageSpinner />;

  if (!user) {
    if (isTelegramWebApp()) return <TelegramLoading />;
    return <Navigate to="/auth" replace state={{ from: location }} />;
  }

  if (!user.onboarded && location.pathname !== "/onboarding") {
    return <Navigate to="/onboarding" replace />;
  }

  return children;
}

// /admin gets its own gate, deliberately NOT the shared Gate above: a
// device that previously opened the regular Fidem_Appbot can have a stale,
// non-admin, non-onboarded session sitting in localStorage (both bots share
// this app's storage - see AppContext's admin-bot-retry effect), and the
// shared Gate would bounce that straight into the "create your dating
// profile" onboarding wizard. The Fidemadminbot Mini App must only ever
// show the admin panel or nothing - never any part of the dating app.
function AdminGate({ children }) {
  const { user, loading } = useApp();

  if (loading) return <PageSpinner />;
  if (!user) {
    if (isTelegramWebApp()) return <TelegramLoading />;
    return <Navigate to="/auth" replace />;
  }
  // Admin.jsx itself renders "Faqat admin uchun" when user.is_admin is
  // false - intentionally no redirect here for that case either.
  return children;
}

function RootRoute() {
  const { user, loading } = useApp();

  if (loading) return <PageSpinner />;

  if (!user && isTelegramWebApp()) {
    return <TelegramLoading />;
  }

  if (!user) return <Welcome />;

  // First-time users (incl. Telegram, who are auto-authenticated) see the
  // Welcome/intro screen once before registration. The Welcome CTA sets the
  // welcomed flag, so returning users skip straight to onboarding.
  if (!user.onboarded && !hasSeenWelcome()) return <Welcome />;

  if (!user.onboarded) return <Navigate to="/onboarding" replace />;

  return (
    <Layout>
      <Candidates />
    </Layout>
  );
}

// The hot navigation paths. Their JS chunks are prefetched while the app is
// idle so tapping a tab (or opening a profile/chat) never blocks on a chunk
// download — the #1 source of the "yuklanmoqda" blank spinner on slow
// networks. import() is deduped by webpack, so lazy() resolves instantly
// once the chunk is warm.
function prefetchHotRoutes() {
  import("@/pages/Candidates");
  import("@/pages/ProfileDetail");
  import("@/pages/Messages");
  import("@/pages/Chat");
  import("@/pages/Saved");
  import("@/pages/Me");
  import("@/pages/Withdrawals");
  import("@/pages/Premium");
  import("@/pages/GiftShop");
}

function Inner() {
  const { user } = useApp();

  useEffect(() => {
    const ric = window.requestIdleCallback || ((cb) => setTimeout(cb, 1500));
    const cancel = window.cancelIdleCallback || clearTimeout;
    const id = ric(prefetchHotRoutes);
    return () => cancel(id);
  }, []);

  // Admin.jsx pulls in recharts (a heavy, admin-only dependency) so it's
  // deliberately excluded from prefetchHotRoutes for every regular user -
  // but for an admin, opening the panel (from the browser or the
  // Fidemadminbot Mini App button) is the very first thing they do, so the
  // chunk should already be warm by the time they tap it instead of paying
  // that download on the critical path.
  useEffect(() => {
    if (!user?.is_admin) return;
    const ric = window.requestIdleCallback || ((cb) => setTimeout(cb, 1500));
    const cancel = window.cancelIdleCallback || clearTimeout;
    const id = ric(() => import("@/pages/Admin"));
    return () => cancel(id);
  }, [user?.is_admin]);

  // Keep the theme in sync (and follow system/Telegram changes when set to
  // "system"). The initial class is set by the inline script in index.html.
  useEffect(() => {
    applyTheme();
    const mq = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => { if (getTheme() === "system") applyTheme("system"); };
    mq && mq.addEventListener && mq.addEventListener("change", onChange);
    return () => { mq && mq.removeEventListener && mq.removeEventListener("change", onChange); };
  }, []);

  // Telegram WebApp init (ready/expand/colors) now runs in index.js, before
  // React even mounts, so the native splash hands off as early as possible.

  return (
    <Suspense fallback={<PageSpinner />}>
      <Routes>
        <Route path="/welcome" element={isTelegramWebApp() ? <Navigate to="/" replace /> : <Welcome />} />
        <Route path="/about" element={<About />} />
        <Route path="/faq" element={<FAQ />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/auth" element={isTelegramWebApp() ? <Navigate to="/" replace /> : <Auth />} />
        <Route path="/onboarding" element={<Gate><Onboarding /></Gate>} />
        <Route path="/" element={<RootRoute />} />
        <Route element={<Gate><Layout /></Gate>}>
          <Route path="/candidate/:id" element={<ProfileDetail />} />
          <Route path="/messages" element={<Messages />} />
          <Route path="/chat/:otherId" element={<Chat />} />
          <Route path="/saved" element={<Saved />} />
          <Route path="/me" element={<Me />} />
          <Route path="/me/settings" element={<MeSettings />} />
          <Route path="/privacy-center" element={<PrivacyCenter />} />
          <Route path="/announcements" element={<Announcements />} />
          <Route path="/gifts" element={<GiftShop />} />
          <Route path="/premium" element={<Premium />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/personality" element={<Personality />} />
          <Route path="/prompts" element={<Prompts />} />
          <Route path="/stories" element={<Stories />} />
          <Route path="/withdrawals" element={<Withdrawals />} />
          <Route path="/family" element={<Family />} />
          <Route path="/concierge" element={<Concierge />} />
          <Route path="/verification" element={<Verification />} />
          <Route path="/referral" element={<Referral />} />
          <Route path="/rankings" element={<Rankings />} />
        </Route>
        <Route path="/admin" element={<AdminGate><Layout><Admin /></Layout></AdminGate>} />
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
          {/* Keep toasts from piling up and covering the screen on rapid taps:
              at most 2 at once, short-lived, not expanded. */}
          <Toaster position="top-center" richColors visibleToasts={2} duration={2000} expand={false} gap={8} />
          <Inner />
        </BrowserRouter>
      </AppProvider>
    </ErrorBoundary>
  );
}
