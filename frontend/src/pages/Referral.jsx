import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, Copy, Send, Users, Gift, Sparkles } from "lucide-react";
import api from "@/lib/api";
import { toast } from "sonner";
import { useApp } from "@/contexts/AppContext";

export default function Referral() {
  const { user } = useApp();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/referral/mine").then((r) => setData(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const code = data?.code || "";
  const inviteLink = code ? `${window.location.origin}/auth?ref=${code}` : "";
  const tgLink = code ? `https://t.me/Fidem_Appbot?start=ref_${code}` : "";

  const copy = (text, label) => {
    navigator.clipboard.writeText(text).then(() => toast.success(`${label} nusxalandi`)).catch(() => toast.error("Nusxalashda xato"));
  };

  const share = () => {
    const text = `🌹 FIDEM — Halal tanishuv platformasi\n\nMening taklif havolam: ${inviteLink}\n\nRo'yxatdan o'tib bepul VIP bonusini oling!`;
    if (navigator.share) {
      navigator.share({ title: "FIDEM", text }).catch(() => {});
    } else {
      copy(text, "Matn");
    }
  };

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <Link to="/me" className="p-2 -ml-2 rounded-full hover:bg-muted" data-testid="ref-back">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <span className="font-heading font-bold text-lg">Do'st taklifi</span>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        <section className="text-center space-y-3">
          <div className="text-6xl">🎁</div>
          <h1 className="text-2xl font-heading font-bold">Do'stlaringizni taklif eting</h1>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            Har bir taklif qilingan do'stingiz uchun <b className="text-primary">+10,000 so'm</b> bonus. 5 ta taklif uchun <b className="text-primary">1 hafta bepul VIP</b>.
          </p>
        </section>

        {loading ? (
          <div className="text-center text-sm text-muted-foreground py-8">Yuklanmoqda...</div>
        ) : (
          <>
            {/* Stats */}
            <section className="grid grid-cols-3 gap-2">
              <div className="rounded-2xl border border-border bg-card p-3 text-center" data-testid="ref-stat-invites">
                <Users className="w-5 h-5 mx-auto text-primary mb-1" />
                <p className="text-xl font-heading font-bold">{data?.invites_count ?? 0}</p>
                <p className="text-[11px] text-muted-foreground">Takliflar</p>
              </div>
              <div className="rounded-2xl border border-border bg-card p-3 text-center" data-testid="ref-stat-earned">
                <Gift className="w-5 h-5 mx-auto text-secondary mb-1" />
                <p className="text-xl font-heading font-bold">{(data?.earned ?? 0).toLocaleString()}</p>
                <p className="text-[11px] text-muted-foreground">so'm topildi</p>
              </div>
              <div className="rounded-2xl border border-border bg-card p-3 text-center" data-testid="ref-stat-progress">
                <Sparkles className="w-5 h-5 mx-auto text-gold-dark mb-1" />
                <p className="text-xl font-heading font-bold">{Math.min(data?.invites_count ?? 0, 5)} / 5</p>
                <p className="text-[11px] text-muted-foreground">VIP bonus</p>
              </div>
            </section>

            {/* Invite link */}
            <section className="rounded-3xl border border-border bg-card p-4 space-y-3">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Sizning kodingiz</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 rounded-xl bg-muted/50 px-4 py-3 font-mono text-lg font-semibold tracking-wider text-center" data-testid="ref-code">
                  {code || "—"}
                </div>
                <button
                  data-testid="ref-copy-code"
                  onClick={() => copy(code, "Kod")}
                  className="p-3 rounded-xl bg-primary text-white"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1.5">Taklif havolasi</p>
                <div className="flex items-center gap-2">
                  <div className="flex-1 rounded-xl bg-muted/30 px-3 py-2 text-xs truncate" data-testid="ref-link">{inviteLink}</div>
                  <button
                    data-testid="ref-copy-link"
                    onClick={() => copy(inviteLink, "Havola")}
                    className="p-2 rounded-xl border border-border"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <button
                data-testid="ref-share"
                onClick={share}
                className="w-full rounded-2xl bg-primary text-white py-3 font-medium flex items-center justify-center gap-2"
              >
                <Send className="w-4 h-4" /> Do'stlarga ulashish
              </button>
              <a
                href={`https://t.me/share/url?url=${encodeURIComponent(inviteLink)}&text=${encodeURIComponent("FIDEM — Halal tanishuv platformasiga taklif qilaman!")}`}
                target="_blank"
                rel="noreferrer"
                data-testid="ref-share-tg"
                className="w-full rounded-2xl border-2 border-border py-3 font-medium flex items-center justify-center gap-2"
              >
                ✈️ Telegram orqali ulashish
              </a>
            </section>

            {/* How it works */}
            <section className="rounded-3xl border border-border bg-card p-4 space-y-3">
              <h2 className="font-heading font-semibold">Qanday ishlaydi?</h2>
              <div className="space-y-2 text-sm">
                <div className="flex gap-3">
                  <span className="w-7 h-7 rounded-full bg-primary text-white grid place-items-center text-xs shrink-0">1</span>
                  <p>Yuqoridagi havolani do'stlaringizga yuboring</p>
                </div>
                <div className="flex gap-3">
                  <span className="w-7 h-7 rounded-full bg-primary text-white grid place-items-center text-xs shrink-0">2</span>
                  <p>Do'stingiz ro'yxatdan o'tib profilini to'liq tasdiqlasin</p>
                </div>
                <div className="flex gap-3">
                  <span className="w-7 h-7 rounded-full bg-primary text-white grid place-items-center text-xs shrink-0">3</span>
                  <p>Siz +10,000 so'm bonus, do'stingiz +5,000 so'm bonus oladi</p>
                </div>
                <div className="flex gap-3">
                  <span className="w-7 h-7 rounded-full bg-gold-dark text-white grid place-items-center text-xs shrink-0">★</span>
                  <p><b>5 ta taklif</b> uchun <b>1 hafta bepul VIP</b> (199,000 so'm qiymatida)</p>
                </div>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
