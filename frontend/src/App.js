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
