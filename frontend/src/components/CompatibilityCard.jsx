import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Sparkles, Lock } from "lucide-react";
import { toast } from "sonner";
import { useApp } from "@/contexts/AppContext";

export default function CompatibilityCard({ targetId }) {
  const { t, lang } = useApp();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [unlocking, setUnlocking] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get(`/personality/compatibility/${targetId}?lang=${lang}`);
      setData(r.data);
    } catch (e) {
      setData({ error: true });
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [targetId, lang]);

  const unlock = async () => {
    setUnlocking(true);
    try {
      await api.post(`/personality/compatibility/${targetId}/unlock`);
      toast.success(t("compat_unlocked"));
      load();
    } catch (e) {
      toast.error(t("insufficient_balance"));
    } finally { setUnlocking(false); }
  };

  if (loading) return <div className="rounded-2xl bg-card border border-border p-4 text-sm text-muted-foreground">{t("loading")}</div>;
  if (!data || data.error) {
    return (
      <div className="rounded-2xl border-2 border-dashed border-secondary/40 bg-secondary/5 p-4 text-center">
        <Sparkles className="w-5 h-5 text-secondary mx-auto mb-1" />
        <p className="text-sm font-medium">{t("compat_take_test")}</p>
        <p className="text-xs text-muted-foreground mt-1">{t("compat_take_test_hint")}</p>
        <a href="/personality" className="mt-3 inline-block rounded-xl bg-secondary text-white px-4 py-2 text-xs font-medium">{t("start_test")}</a>
      </div>
    );
  }

  const unlockLabel = t("compat_unlock_btn")
    .replace("{price}", "20,000")
    .replace("{currency}", t("sum"));

  return (
    <div className="rounded-2xl border-2 border-primary/30 bg-primary/5 p-4" data-testid="compat-card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary" />
          <h3 className="font-heading font-semibold">{t("compat_title")}</h3>
        </div>
        <div className="text-3xl font-heading font-semibold text-primary">{data.score}<span className="text-base text-muted-foreground">/100</span></div>
      </div>

      {data.locked ? (
        <>
          <div className="rounded-xl bg-card/60 backdrop-blur p-3 mb-3">
            <p className="text-xs text-muted-foreground">{t("compat_basic_score").replace("{score}", data.score)}</p>
          </div>
          <button data-testid="unlock-compat" onClick={unlock} disabled={unlocking} className="w-full rounded-2xl bg-primary text-white py-2.5 text-sm font-medium inline-flex items-center justify-center gap-2 disabled:opacity-50">
            <Lock className="w-4 h-4" /> {unlockLabel}
          </button>
          <p className="text-[11px] text-muted-foreground mt-2 text-center">{t("compat_premium_free")}</p>
        </>
      ) : data.report ? (
        <div className="space-y-3">
          <p className="text-sm leading-relaxed">{data.report.summary}</p>
          {data.report.strengths?.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">{t("compat_strengths")}</p>
              <ul className="space-y-1">
                {data.report.strengths.map((s, i) => (<li key={i} className="text-sm flex gap-2"><span className="text-secondary">✓</span>{s}</li>))}
              </ul>
            </div>
          )}
          {data.report.watch_outs?.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">{t("compat_watch_outs")}</p>
              <ul className="space-y-1">
                {data.report.watch_outs.map((s, i) => (<li key={i} className="text-sm flex gap-2"><span className="text-gold-dark">⚠</span>{s}</li>))}
              </ul>
            </div>
          )}
          {data.report.conversation_starters?.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">{t("compat_conversation")}</p>
              <ul className="space-y-1">
                {data.report.conversation_starters.map((s, i) => (<li key={i} className="text-sm flex gap-2"><span className="text-primary">💬</span>{s}</li>))}
              </ul>
            </div>
          )}
          {!data.report.ai_generated && (
            <p className="text-[10px] text-muted-foreground italic">{t("compat_ai_fallback")}</p>
          )}
        </div>
      ) : null}
    </div>
  );
}
