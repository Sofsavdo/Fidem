import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { VerifiedBadge, FinancialBadge, PlanPill } from "@/components/Badges";
import { ChevronRight, Crown, Gem, Wallet, Share2, Settings, LogOut, Copy, Trophy, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

export default function Me() {
  const { user, t, logout, changeLang, lang, refresh } = useApp();
  const [referral, setReferral] = useState(null);
  const [leaders, setLeaders] = useState([]);
  const [leadPeriod, setLeadPeriod] = useState("all");

  useEffect(() => {
    api.get("/referral/mine").then((r) => setReferral(r.data));
  }, []);
  useEffect(() => {
    api.get(`/leaderboard?period=${leadPeriod}`).then((r) => setLeaders(r.data || []));
  }, [leadPeriod]);

  if (!user) return null;

  const copy = (txt) => {
    navigator.clipboard.writeText(txt).then(() => toast.success(t("copied")));
  };

  const requestVerification = async (kind) => {
    try {
      await api.post("/verification/request", { kind });
      toast.success("So'rov yuborildi");
      refresh();
    } catch (e) { toast.error("Xato"); }
  };

  return (
    <div className="px-4 pt-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-3xl font-semibold tracking-tight">{t("me")}</h1>
        <select
          data-testid="me-lang"
          value={lang}
          onChange={(e) => changeLang(e.target.value)}
          className="text-xs bg-transparent border border-border rounded-full px-2.5 py-1"
        >
          <option value="uz">UZ</option>
          <option value="ru">RU</option>
          <option value="en">EN</option>
        </select>
      </div>

      {/* Profile card */}
      <div className="rounded-3xl bg-card border border-border p-4 flex items-center gap-4 shadow-soft" data-testid="me-profile-card">
        <div className="relative w-16 h-16 rounded-2xl bg-muted overflow-hidden flex-shrink-0">
          {user.photo_url ? (
            <img src={user.photo_url} alt="" className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full grid place-items-center text-muted-foreground text-xl font-heading">{user.name?.[0]}</div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="font-medium text-lg truncate">{user.name}, {user.age}</p>
            <PlanPill plan={user.plan} />
          </div>
          <p className="text-xs text-muted-foreground truncate">{user.region} · {user.profession || "—"}</p>
          <div className="flex gap-1 mt-1.5 flex-wrap">
            <VerifiedBadge verified={user.verified_selfie} />
            <FinancialBadge verified={user.verified_financial} />
            {user.verified_identity && (
              <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 text-blue-700 border border-blue-100 px-2 py-0.5 text-[10px]">
                <ShieldCheck className="w-3 h-3" /> Identity
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Completeness */}
      <div className="rounded-3xl bg-card border border-border p-4">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs uppercase tracking-wider text-muted-foreground">{t("completeness")}</p>
          <p className="text-sm font-semibold" data-testid="me-completeness">{user.completeness || 0}%</p>
        </div>
        <div className="h-2 rounded-full bg-border overflow-hidden">
          <div
            className={`h-full transition-all ${user.completeness === 100 ? "bg-gold" : "bg-primary"}`}
            style={{ width: `${user.completeness || 0}%` }}
          />
        </div>
      </div>

      {/* Premium/balance row */}
      <div className="grid grid-cols-2 gap-3">
        <Link to="/premium" data-testid="link-premium" className="rounded-3xl bg-gradient-to-br from-ink to-zinc-800 text-white p-4 hover:-translate-y-0.5 transition-transform">
          <Crown className="w-5 h-5 text-gold" />
          <p className="font-heading text-lg mt-2">{t("premium")}</p>
          <p className="text-xs text-white/70 mt-0.5">Tariflar →</p>
        </Link>
        <Link to="/premium?topup=1" data-testid="link-balance" className="rounded-3xl bg-card border border-border p-4 hover:-translate-y-0.5 transition-transform">
          <Wallet className="w-5 h-5 text-primary" />
          <p className="font-heading text-lg mt-2">{(user.balance || 0).toLocaleString()} so'm</p>
          <p className="text-xs text-muted-foreground mt-0.5">{t("balance")}</p>
        </Link>
      </div>

      {/* Verification actions */}
      <div className="rounded-3xl bg-card border border-border divide-y">
        <Row
          icon={<ShieldCheck className="w-4 h-4 text-secondary" />}
          label={t("request_selfie")}
          right={user.verified_selfie ? <span className="text-secondary text-xs">✓</span> : <button data-testid="req-verify-selfie" onClick={() => requestVerification("selfie")} className="text-xs text-primary font-medium">{t("request_verification")}</button>}
        />
        <Row
          icon={<Gem className="w-4 h-4 text-gold-dark" />}
          label={t("financial_verification")}
          right={user.verified_financial ? <span className="text-secondary text-xs">✓</span> : <button data-testid="req-verify-financial" onClick={() => requestVerification("financial")} className="text-xs text-primary font-medium">{t("request_verification")}</button>}
        />
      </div>

      {/* Referral */}
      {referral && (
        <div className="rounded-3xl bg-card border border-border p-4" data-testid="referral-card">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Share2 className="w-4 h-4 text-secondary" />
              <p className="font-heading text-lg">{t("referral")}</p>
            </div>
            <span className="text-xs text-muted-foreground">{referral.invited_count} invited</span>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <code className="flex-1 truncate text-xs bg-muted rounded-xl px-3 py-2">{referral.link}</code>
            <button data-testid="copy-referral" onClick={() => copy(referral.link)} className="rounded-xl border border-border px-3 py-2">
              <Copy className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Leaderboard */}
      <div className="rounded-3xl bg-card border border-border p-4" data-testid="leaderboard-card">
        <div className="flex items-center gap-2">
          <Trophy className="w-4 h-4 text-gold-dark" />
          <p className="font-heading text-lg">{t("top_supporters")}</p>
        </div>
        <div className="flex gap-1 mt-3 mb-3">
          {[
            ["day", t("daily")],
            ["week", t("weekly")],
            ["month", t("monthly")],
            ["all", t("all_time")],
          ].map(([k, l]) => (
            <button
              key={k}
              data-testid={`lead-${k}`}
              onClick={() => setLeadPeriod(k)}
              className={`text-[10px] px-2 py-1 rounded-full border ${
                leadPeriod === k ? "bg-foreground text-background border-foreground" : "bg-card border-border"
              }`}
            >
              {l}
            </button>
          ))}
        </div>
        <div className="space-y-2">
          {leaders.length === 0 && <p className="text-xs text-muted-foreground">{t("no_data")}</p>}
          {leaders.slice(0, 10).map((row, i) => (
            <div key={row.user.id} className="flex items-center gap-3 text-sm">
              <span className="w-5 text-center font-medium text-muted-foreground">{i + 1}</span>
              <div className="w-7 h-7 rounded-full bg-muted overflow-hidden">
                {row.user.photo_url && <img src={row.user.photo_url} alt="" className="w-full h-full object-cover" />}
              </div>
              <span className="flex-1 truncate">{row.user.name}</span>
              <span className="text-gold-dark font-medium">{row.total.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Admin & settings */}
      <div className="rounded-3xl bg-card border border-border divide-y">
        {user.is_admin && (
          <Link to="/admin" data-testid="link-admin" className="flex items-center justify-between p-4">
            <span className="flex items-center gap-3 text-sm"><Settings className="w-4 h-4" /> {t("admin_panel")}</span>
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          </Link>
        )}
        <button data-testid="btn-logout" onClick={logout} className="flex items-center justify-between p-4 w-full text-left">
          <span className="flex items-center gap-3 text-sm text-primary"><LogOut className="w-4 h-4" /> {t("logout")}</span>
        </button>
      </div>
    </div>
  );
}

function Row({ icon, label, right }) {
  return (
    <div className="flex items-center justify-between p-4">
      <span className="flex items-center gap-3 text-sm">{icon} {label}</span>
      <div>{right}</div>
    </div>
  );
}
