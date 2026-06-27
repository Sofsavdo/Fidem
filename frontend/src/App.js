import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AppProvider, useApp } from "@/contexts/AppContext";
import Layout from "@/components/Layout";
import Auth from "@/pages/Auth";
import Onboarding from "@/pages/Onboarding";
import Candidates from "@/pages/Candidates";
import ProfileDetail from "@/pages/ProfileDetail";
import Messages from "@/pages/Messages";
import Chat from "@/pages/Chat";
import Saved from "@/pages/Saved";
import Me from "@/pages/Me";
import Premium from "@/pages/Premium";
import Admin from "@/pages/Admin";
import Settings from "@/pages/Settings";
import Notifications from "@/pages/Notifications";
import Quiz from "@/pages/Quiz";
import Boost from "@/pages/Boost";
import Personality from "@/pages/Personality";
import Chaperone from "@/pages/Chaperone";
import ChaperoneWard from "@/pages/ChaperoneWard";
import Prompts from "@/pages/Prompts";
import Stories from "@/pages/Stories";

function Gate({ children }) {
  const { user, loading } = useApp();
  const location = useLocation();
  if (loading) return <div className="min-h-screen grid place-items-center text-muted-foreground">Loading...</div>;
  if (!user) return <Navigate to="/auth" replace state={{ from: location }} />;
  if (!user.onboarded && location.pathname !== "/onboarding") return <Navigate to="/onboarding" replace />;
  return children;
}

function Inner() {
  // Inject Telegram WebApp script at runtime
  useEffect(() => {
    if (window.Telegram?.WebApp) return;
    const s = document.createElement("script");
    s.src = "https://telegram.org/js/telegram-web-app.js";
    s.async = true;
    document.head.appendChild(s);
  }, []);

  return (
    <Routes>
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
        <Route path="/boost" element={<Boost />} />
        <Route path="/admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Toaster position="top-center" richColors />
        <Inner />
      </BrowserRouter>
    </AppProvider>
  );
}
