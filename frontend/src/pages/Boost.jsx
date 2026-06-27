import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { ArrowLeft, Sparkles, Star, Rocket } from "lucide-react";
import { toast } from "sonner";

export default function Boost() {
  const { t, user, refresh } = useApp();
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = () => api.get("/boost/status").then((r) => setStatus(r.data));
  useEffect(() => { load(); }, []);

  const activate = async (kind) => {
    setBusy(true);
    try {
      const r = await api.post(`/${kind}/activate`, { use_balance: true });
      toast.success(kind === "boost" ? "Boost faollashtirildi 🚀" : "Spotlight faollashtirildi 🌟");
      await refresh();
      load();
    } catch (e) {
      const msg = e.response?.data?.detail;
      if (msg && msg.includes("Need")) {
        toast.error(`${msg} — balansni to'ldiring`);
      } else {
        toast.error(msg || "Xato");
      }
    } finally {
      setBusy(false);
    }
  };

  const payViaClick = async (purpose, amount) => {
    try {
      const r = await api.post("/payments/create", { purpose: "balance_topup", amount });
      window.open(r.data.payment_link, "_blank");
      toast.success("To'lov sahifasi ochildi — to'lovdan keyin balansni avto-yangilaymiz");
    } catch (e) {
      toast.error("Xato");
    }
  };

  return (
    <div className="px-4 md:px-8 pt-6 pb-8 space-y-5" data-testid="boost-page">
      <div className="flex items-center gap-3">
        <Link to="/me" className="p-2 rounded-full hover:bg-muted" data-testid="boost-back">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <h1 className="font-heading text-2xl md:text-3xl font-semibold tracking-tight">Boost & Spotlight</h1>
          <p className="text-xs text-muted-foreground">Profilingizni ko'proq odamlar ko'rishi uchun</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {/* Boost */}
        <div className="rounded-3xl border-2 border-primary/30 bg-gradient-to-br from-primary/5 to-card p-5" data-testid="card-boost">
          <div className="flex items-center justify-between">
            <Rocket className="w-7 h-7 text-primary" />
            <span className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary font-medium">24 SOAT</span>
          </div>
          <h2 className="font-heading text-2xl font-semibold mt-3">Profile Boost</h2>
          <p className="text-sm text-muted-foreground mt-1">24 soat davomida nomzodlar oqimida 5x ko'proq ko'rinasiz.</p>
          <ul className="text-sm mt-3 space-y-1">
            <li>✓ Top of feed</li>
            <li>✓ Profil ko'rishlar 3-5x oshadi</li>
            <li>✓ Tezroq xabarlar oqimi</li>
          </ul>
          <p className="font-heading text-xl mt-4">5,000 so'm</p>
          {status?.active && (
            <p className="text-xs text-secondary mt-2">Faol — {new Date(status.until).toLocaleString()}</p>
          )}
          <div className="flex flex-col sm:flex-row gap-2 mt-3">
            <button
              data-testid="buy-boost-balance"
              onClick={() => activate("boost")}
              disabled={busy || status?.active}
              className="flex-1 rounded-2xl bg-primary text-white py-3 font-medium disabled:opacity-50"
            >
              Balans bilan ({(user?.balance || 0).toLocaleString()})
            </button>
            <button
              data-testid="buy-boost-click"
              onClick={() => payViaClick("boost", 5000)}
              className="flex-1 rounded-2xl border border-border bg-card py-3 font-medium hover:bg-muted"
            >
              CLICK
            </button>
          </div>
        </div>

        {/* Spotlight */}
        <div className="rounded-3xl border-2 border-gold/40 bg-gradient-to-br from-gold-light/30 to-card p-5" data-testid="card-spotlight">
          <div className="flex items-center justify-between">
            <Star className="w-7 h-7 text-gold-dark" fill="currentColor" />
            <span className="text-xs px-2 py-1 rounded-full bg-gold-light text-yellow-900 font-medium">7 KUN</span>
          </div>
          <h2 className="font-heading text-2xl font-semibold mt-3">Spotlight</h2>
          <p className="text-sm text-muted-foreground mt-1">1 hafta davomida o'z viloyatingiz feed'ida birinchi qatorda.</p>
          <ul className="text-sm mt-3 space-y-1">
            <li>★ Region top placement</li>
            <li>★ Spotlight badge</li>
            <li>★ Doimiy visibility</li>
          </ul>
          <p className="font-heading text-xl mt-4">25,000 so'm</p>
          <div className="flex flex-col sm:flex-row gap-2 mt-3">
            <button
              data-testid="buy-spotlight-balance"
              onClick={() => activate("spotlight")}
              disabled={busy}
              className="flex-1 rounded-2xl bg-gold text-ink py-3 font-medium disabled:opacity-50"
            >
              Balans bilan
            </button>
            <button
              data-testid="buy-spotlight-click"
              onClick={() => payViaClick("spotlight", 25000)}
              className="flex-1 rounded-2xl border border-border bg-card py-3 font-medium hover:bg-muted"
            >
              CLICK
            </button>
          </div>
        </div>
      </div>

      <p className="text-xs text-muted-foreground text-center pt-2">
        💡 Maslahat: Spotlight + Premium birlashtirilsa, sizning profilingiz konversiyasi 10x oshadi
      </p>
    </div>
  );
}
