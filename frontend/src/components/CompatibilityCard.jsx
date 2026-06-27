import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Sparkles, Lock } from "lucide-react";
import { toast } from "sonner";

export default function CompatibilityCard({ targetId, lang = "uz" }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [unlocking, setUnlocking] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get(`/personality/compatibility/${targetId}?lang=${lang}`);
      setData(r.data);
    } catch (e) {
      // Probably user hasn't completed Big5 yet
      setData({ error: true });
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [targetId, lang]);

  const unlock = async () => {
    setUnlocking(true);
    try {
      await api.post(`/personality/compatibility/${targetId}/unlock`);
      toast.success("AI hisobot ochildi");
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Balans yetarli emas");
    } finally { setUnlocking(false); }
  };

  if (loading) return <div className="rounded-2xl bg-card border border-border p-4 text-sm text-muted-foreground">Yuklanmoqda…</div>;
  if (!data || data.error) {
    return (
      <div className="rounded-2xl border-2 border-dashed border-secondary/40 bg-secondary/5 p-4 text-center">
        <Sparkles className="w-5 h-5 text-secondary mx-auto mb-1" />
        <p className="text-sm font-medium">Shaxsiyat testini topshiring</p>
        <p className="text-xs text-muted-foreground mt-1">AI moslik hisobotini ochish uchun avval Big 5 testini topshiring.</p>
        <a href="/personality" className="mt-3 inline-block rounded-xl bg-secondary text-white px-4 py-2 text-xs font-medium">Testni boshlash</a>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border-2 border-primary/30 bg-primary/5 p-4" data-testid="compat-card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary" />
          <h3 className="font-heading font-semibold">AI Moslik tahlili</h3>
        </div>
        <div className="text-3xl font-heading font-semibold text-primary">{data.score}<span className="text-base text-muted-foreground">/100</span></div>
      </div>

      {data.locked ? (
        <>
          <div className="rounded-xl bg-card/60 backdrop-blur p-3 mb-3">
            <p className="text-xs text-muted-foreground">Asosiy moslik: {data.score}/100</p>
          </div>
          <button data-testid="unlock-compat" onClick={unlock} disabled={unlocking} className="w-full rounded-2xl bg-primary text-white py-2.5 text-sm font-medium inline-flex items-center justify-center gap-2 disabled:opacity-50">
            <Lock className="w-4 h-4" /> AI Hisobotni ochish (20,000 so'm)
          </button>
          <p className="text-[11px] text-muted-foreground mt-2 text-center">Premium foydalanuvchilar uchun bepul</p>
        </>
      ) : data.report ? (
        <div className="space-y-3">
          <p className="text-sm leading-relaxed">{data.report.summary}</p>
          {data.report.strengths?.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Kuchli moslik nuqtalari</p>
              <ul className="space-y-1">
                {data.report.strengths.map((s, i) => (<li key={i} className="text-sm flex gap-2"><span className="text-secondary">✓</span>{s}</li>))}
              </ul>
            </div>
          )}
          {data.report.watch_outs?.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">E'tibor bering</p>
              <ul className="space-y-1">
                {data.report.watch_outs.map((s, i) => (<li key={i} className="text-sm flex gap-2"><span className="text-gold-dark">⚠</span>{s}</li>))}
              </ul>
            </div>
          )}
          {data.report.conversation_starters?.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Suhbat savollari</p>
              <ul className="space-y-1">
                {data.report.conversation_starters.map((s, i) => (<li key={i} className="text-sm flex gap-2"><span className="text-primary">💬</span>{s}</li>))}
              </ul>
            </div>
          )}
          {!data.report.ai_generated && (
            <p className="text-[10px] text-muted-foreground italic">* AI hozirda mavjud emas, default hisobot ko'rsatildi</p>
          )}
        </div>
      ) : null}
    </div>
  );
}
