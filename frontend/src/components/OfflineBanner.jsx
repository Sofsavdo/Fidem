import React from "react";
import { WifiOff } from "lucide-react";
import { useApp } from "@/contexts/AppContext";

/**
 * Sticky banner shown when navigator is offline.
 * Disappears on reconnection.
 */
export default function OfflineBanner() {
  const { t, isOnline } = useApp();

  if (isOnline) return null;
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
