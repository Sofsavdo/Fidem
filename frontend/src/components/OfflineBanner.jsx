import React, { useEffect, useState } from "react";
import { WifiOff } from "lucide-react";
import { useApp } from "@/contexts/AppContext";

/**
 * Sticky banner shown when navigator is offline.
 * Disappears on reconnection.
 */
export default function OfflineBanner() {
  const { t } = useApp();
  const [online, setOnline] = useState(typeof navigator !== "undefined" ? navigator.onLine : true);

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  if (online) return null;
  const label = (typeof t === "function" && t("offline_banner")) || "📴 Internet aloqasi yo'q";

  return (
    <div
      data-testid="offline-banner"
      className="fixed top-0 inset-x-0 z-[60] bg-rose-600 text-white text-center text-sm py-2 px-3 flex items-center justify-center gap-2 shadow-lg"
      style={{ paddingTop: "max(8px, env(safe-area-inset-top))" }}
    >
      <WifiOff className="w-4 h-4" />
      <span>{label}</span>
    </div>
  );
}
