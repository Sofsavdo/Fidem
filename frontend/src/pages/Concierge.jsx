import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { Sparkles, Crown, CheckCircle2, Clock, Heart } from "lucide-react";
import { photoSrc } from "@/lib/photo";
import { Link } from "react-router-dom";

export default function Concierge() {
  const [info, setInfo] = useState(null);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    try {
      const [i, o] = await Promise.all([api.get("/concierge/info"), api.get("/concierge/mine")]);
      setInfo(i.data);
      setOrders(o.data || []);
    } catch (e) { /* ignore */ }
  };

  useEffect(() => { load(); }, []);

  const order = async (method) => {
    setLoading(true);
    try {
      const r = await api.post("/concierge/order", { payment_method: method });
      if (r.data.payment_link) {
        toast.info("To'lov sahifasiga yo'naltirilmoqda...");
        setTimeout(() => { window.open(r.data.payment_link, "_blank"); }, 600);
      } else {
        toast.success("🎉 Sovchi Concierge faollashtirildi! Admin sizga 5 ta mosni qo'lda topadi.");
      }
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Xato");
    } finally { setLoading(false); }
  };

  if (!info) return <div className="p-6 text-muted-foreground">Yuklanmoqda...</div>;

  return (
    <div className="max-w-3xl mx-auto p-4 md:p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-heading font-semibold flex items-center gap-2">
          <Sparkles className="w-6 h-6 text-secondary" /> Sovchi Concierge
        </h1>
        <p className="text-sm text-muted-foreground mt-1">Professional sovchi sizga shaxsan 5 ta eng mos nomzodni qo'lda tanlab beradi.</p>
      </div>

      {/* Pricing card */}
      <div className="rounded-3xl bg-gradient-to-br from-primary/15 via-secondary/10 to-gold-light/20 border border-border p-6 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-secondary text-white">
              <Crown className="w-3 h-3" /> PREMIUM XIZMAT
            </div>
            <h2 className="text-3xl font-heading font-semibold mt-2">{info.price.toLocaleString()} so'm</h2>
            <p className="text-sm text-muted-foreground">{info.days} kun ichida {info.max_matches} ta tanlangan mos</p>
          </div>
          <Heart className="w-10 h-10 text-primary/30" fill="currentColor" />
        </div>
        <ul className="text-sm space-y-2">
          <li className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" /> Admin sizning profilingiz va Big 5 testingizni chuqur tahlil qiladi</li>
          <li className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" /> Qo'lda tanlangan {info.max_matches} ta yuqori sifatli mos taqdim etiladi</li>
          <li className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" /> Har bir mos haqida sovchi izohi (nima sababdan moskelishi)</li>
          <li className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" /> Avtomatik tanlovdan farqli o'laroq — inson nazorati</li>
        </ul>
        {!info.active_order && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <button data-testid="concierge-click" onClick={() => order("click")} disabled={loading} className="py-3 rounded-2xl bg-primary text-white font-medium disabled:opacity-50">
              CLICK orqali to'lash
            </button>
            <button data-testid="concierge-balance" onClick={() => order("balance")} disabled={loading || !info.can_balance_pay} className="py-3 rounded-2xl border-2 border-primary text-primary font-medium disabled:opacity-30">
              Balansdan to'lash {info.can_balance_pay ? "✓" : "(yetarli emas)"}
            </button>
          </div>
        )}
      </div>

      {/* Active order */}
      {orders.length > 0 && (
        <div className="space-y-4">
          <h2 className="font-semibold">Mening buyurtmalarim</h2>
          {orders.map((o) => (
            <div key={o.id} className="rounded-3xl border border-border bg-card p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm"><span className="font-medium">{o.amount.toLocaleString()} so'm</span> · {new Date(o.created_at).toLocaleDateString("uz-UZ")}</p>
                  <p className="text-xs text-muted-foreground">Status: {statusLabel(o.status)}</p>
                </div>
                <span className="text-xs font-medium">{(o.matches || []).length}/{info.max_matches} mos</span>
              </div>
              {(o.match_users || []).length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {o.match_users.map((m) => (
                    <Link key={m.id} to={`/candidate/${m.id}`} className="flex items-center gap-3 p-3 rounded-xl bg-muted/40 hover:bg-muted transition">
                      <div className="w-12 h-12 rounded-xl bg-muted overflow-hidden">
                        {m.photo_url && <img src={photoSrc(m.photo_url)} alt="" className="w-full h-full object-cover" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">{m.name}, {m.age}</p>
                        <p className="text-xs text-muted-foreground truncate">{m.region} · {m.profession}</p>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : o.status === "in_progress" ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock className="w-4 h-4" /> Admin sizga moslarni izlamoqda...
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function statusLabel(s) {
  return ({
    awaiting_payment: "To'lov kutilmoqda",
    in_progress: "Sovchi izlamoqda",
    active: "Faol",
    completed: "Tugatildi",
    expired: "Muddati o'tdi",
  })[s] || s;
}
