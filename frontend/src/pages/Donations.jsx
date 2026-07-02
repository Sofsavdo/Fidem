import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, Gift, TrendingUp, Info } from "lucide-react";
import api from "@/lib/api";
import { toast } from "sonner";
import { useApp } from "@/contexts/AppContext";

export default function Donations() {
  const { t } = useApp();
  const [rates, setRates] = useState(null);
  const [history, setHistory] = useState(null);
  const [source, setSource] = useState("balance");
  const [amount, setAmount] = useState("");
  const [loading, setLoading] = useState(false);
  const [converting, setConverting] = useState(false);

  const load = async () => {
    try {
      const [r, h] = await Promise.all([
        api.get("/donation/rates"),
        api.get("/donation/history")
      ]);
      setRates(r.data);
      setHistory(h.data);
    } catch {/* ignore */}
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const convert = async () => {
    const amt = parseInt(amount, 10);
    if (!amt || amt < 10000) {
      toast.error("Minimum conversion: 10,000 so'm");
      return;
    }
    if (amt > 500000) {
      toast.error("Maximum conversion: 500,000 so'm");
      return;
    }
    setConverting(true);
    try {
      await api.post("/donation/convert", { source, amount: amt });
      toast.success("Converted successfully");
      setAmount("");
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Conversion failed");
    } finally { setConverting(false); }
  };

  if (loading) return <div className="p-6 text-muted-foreground">{t("loading")}</div>;

  const currentBonus = rates?.current_bonus || 10;
  const influenceGained = amount ? Math.floor(parseInt(amount) * (1 + currentBonus / 100)) : 0;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <Link to="/economy" className="p-2 -ml-2 rounded-full hover:bg-muted">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <span className="font-heading font-bold text-lg">Convert to Influence</span>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* Current Rates */}
        <section className="rounded-3xl border border-border bg-gradient-to-br from-primary/10 to-secondary/10 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-2xl bg-primary text-white grid place-items-center">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Current Bonus</p>
              <p className="text-2xl font-heading font-semibold">+{currentBonus}%</p>
            </div>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Standard</span>
              <span>{rates?.standard_bonus}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Weekend</span>
              <span>{rates?.weekend_bonus}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Founder</span>
              <span>{rates?.founder_bonus}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Ambassador</span>
              <span>{rates?.ambassador_bonus}%</span>
            </div>
          </div>
          {rates?.is_weekend && (
            <div className="mt-3 text-xs text-foreground font-medium">🎉 Weekend bonus active!</div>
          )}
        </section>

        {/* Conversion Form */}
        <section className="rounded-3xl border border-border bg-card p-6 space-y-4">
          <h2 className="font-heading font-semibold">Convert Balance to Influence</h2>
          
          <div>
            <label className="text-sm text-muted-foreground mb-2 block">Source</label>
            <div className="grid grid-cols-3 gap-2">
              {["balance", "referral_earnings", "bonus"].map((s) => (
                <button
                  key={s}
                  onClick={() => setSource(s)}
                  className={`p-3 rounded-xl text-sm font-medium capitalize ${
                    source === s ? "bg-primary text-white" : "bg-muted/30"
                  }`}
                >
                  {s.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-sm text-muted-foreground mb-2 block">Amount (so'm)</label>
            <input
              type="number"
              placeholder="10,000 - 500,000"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-input bg-background text-sm"
              min={10000}
              max={500000}
            />
          </div>

          {amount && (
            <div className="rounded-xl bg-muted/30 p-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Amount</span>
                <span className="font-medium">{parseInt(amount).toLocaleString()} so'm</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Bonus (+{currentBonus}%)</span>
                <span className="font-medium text-foreground">+{Math.floor(parseInt(amount) * currentBonus / 100).toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-sm font-semibold pt-2 border-t border-border/40">
                <span>Influence Gained</span>
                <span className="text-foreground">{influenceGained.toLocaleString()}</span>
              </div>
            </div>
          )}

          <button
            onClick={convert}
            disabled={converting || !amount}
            className="w-full py-3 rounded-2xl bg-primary text-white font-medium disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Gift className="w-4 h-4" />
            {converting ? "..." : "Convert"}
          </button>
        </section>

        {/* Info */}
        <div className="rounded-2xl border border-border bg-card p-4 flex gap-3 text-sm">
          <Info className="w-4 h-4 text-foreground shrink-0 mt-0.5" />
          <div className="text-muted-foreground">
            <p>Convert your balance or referral earnings to influence score. Influence determines your ranking and status in the community.</p>
          </div>
        </div>

        {/* History */}
        <section className="rounded-3xl border border-border bg-card p-6">
          <h2 className="font-heading font-semibold mb-4">Conversion History</h2>
          {history?.donations?.length === 0 ? (
            <p className="text-sm text-muted-foreground">No conversions yet</p>
          ) : (
            <div className="space-y-2">
              {history?.donations?.slice(-10).reverse().map((d) => (
                <div key={d.id} className="flex items-center justify-between py-2 border-b border-border/40 last:border-0">
                  <div>
                    <p className="text-sm font-medium">{d.source.replace("_", " ")}</p>
                    <p className="text-[11px] text-muted-foreground">{new Date(d.created_at).toLocaleString()}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-foreground">+{d.influence_gained.toLocaleString()}</p>
                    <p className="text-[11px] text-muted-foreground">+{d.bonus_percentage}% bonus</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
