import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, Copy, Send, Users, Gift, Sparkles, Crown, Info } from "lucide-react";
import api from "@/lib/api";
import { toast } from "sonner";
import { useApp } from "@/contexts/AppContext";

export default function Referral() {
  const { t, refresh } = useApp();
  const [data, setData] = useState(null);
  const [usernameData, setUsernameData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [redeeming, setRedeeming] = useState(false);
  const [showUsernameModal, setShowUsernameModal] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [checkingUsername, setCheckingUsername] = useState(false);

  const load = async () => {
    try {
      const [r, u] = await Promise.all([
        api.get("/referral/mine"),
        api.get("/referral/username/status")
      ]);
      setData(r.data);
      setUsernameData(u.data);
    } catch {/* ignore */}
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const code = data?.code || "";
  const inviteLink = data?.link || (code ? `https://t.me/Fidem_Appbot?start=${code}` : "");

  const setUsername = async () => {
    if (!newUsername || newUsername.length < 3 || newUsername.length > 30) {
      toast.error("Username must be 3-30 characters");
      return;
    }
    setCheckingUsername(true);
    try {
      await api.post("/referral/username/set", { username: newUsername });
      toast.success("Username updated successfully");
      setShowUsernameModal(false);
      setNewUsername("");
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to set username");
    } finally { setCheckingUsername(false); }
  };

  const copy = (text, label) => {
    navigator.clipboard.writeText(text).then(() => toast.success(`${label} ${t("copied")}`)).catch(() => toast.error(t("error")));
  };

  const share = () => {
    const subtitle = "🌹 FIDEM";
    const txt = `${subtitle}\n\n${inviteLink}`;
    if (navigator.share) {
      navigator.share({ title: "FIDEM", text: txt }).catch(() => {});
    } else {
      copy(txt, t("share"));
    }
  };

  const redeem = async () => {
    if (!data?.available_weeks) return;
    setRedeeming(true);
    try {
      await api.post("/invites/redeem");
      toast.success("Premium 7 " + t("daily").toLowerCase() + " 🎉");
      await load();
      refresh && refresh();
    } catch (e) {
      toast.error(t("error"));
    } finally { setRedeeming(false); }
  };

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <Link to="/me" className="p-2 -ml-2 rounded-full hover:bg-muted" data-testid="ref-back">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <span className="font-heading font-bold text-lg">{t("ref_title")}</span>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        <section className="text-center space-y-3">
          <div className="text-6xl">🎁</div>
          <h1 className="text-2xl font-heading font-bold">{t("ref_subtitle")}</h1>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            +<b className="text-primary">10,000 {t("sum")}</b> · 5 → <b className="text-primary">1 {t("free_premium_week")}</b>
          </p>
        </section>

        {loading ? (
          <div className="text-center text-sm text-muted-foreground py-8">{t("loading")}</div>
        ) : (
          <>
            {/* Stats */}
            <section className="grid grid-cols-3 gap-2">
              <div className="rounded-2xl border border-border bg-card p-3 text-center" data-testid="ref-stat-invites">
                <Users className="w-5 h-5 mx-auto text-primary mb-1" />
                <p className="text-xl font-heading font-bold">{data?.invited_count ?? 0}</p>
                <p className="text-[11px] text-muted-foreground">{t("ref_invites")}</p>
              </div>
              <div className="rounded-2xl border border-border bg-card p-3 text-center" data-testid="ref-stat-paid">
                <Crown className="w-5 h-5 mx-auto text-gold-dark mb-1" />
                <p className="text-xl font-heading font-bold">{data?.paid_referrals ?? 0}</p>
                <p className="text-[11px] text-muted-foreground">Paid Referrals</p>
              </div>
              <div className="rounded-2xl border border-border bg-card p-3 text-center" data-testid="ref-stat-progress">
                <Sparkles className="w-5 h-5 mx-auto text-gold-dark mb-1" />
                <p className="text-xl font-heading font-bold">{Math.min(data?.invited_count ?? 0, 5)} / 5</p>
                <p className="text-[11px] text-muted-foreground">{t("ref_vip_bonus")}</p>
              </div>
            </section>

            {/* Earnings Breakdown */}
            <section className="rounded-3xl border border-border bg-card p-4 space-y-3">
              <h2 className="font-heading font-semibold flex items-center gap-2">
                <Gift className="w-4 h-4 text-secondary" /> Earnings
              </h2>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="rounded-xl bg-muted/30 p-3">
                  <p className="text-muted-foreground text-xs">{t("referral_earnings_pending")}</p>
                  <p className="font-medium">{(data?.referral_earnings_pending ?? 0).toLocaleString()} {t("sum")}</p>
                </div>
                <div className="rounded-xl bg-muted/30 p-3">
                  <p className="text-muted-foreground text-xs">{t("referral_earnings_approved")}</p>
                  <p className="font-medium">{(data?.referral_earnings_approved ?? 0).toLocaleString()} {t("sum")}</p>
                </div>
                <div className="rounded-xl bg-primary/10 p-3 border border-primary/30">
                  <p className="text-muted-foreground text-xs">{t("referral_earnings_withdrawable")}</p>
                  <p className="font-medium text-primary">{(data?.referral_earnings_withdrawable ?? 0).toLocaleString()} {t("sum")}</p>
                </div>
                <div className="rounded-xl bg-muted/30 p-3">
                  <p className="text-muted-foreground text-xs">{t("referral_earnings_paid_out")}</p>
                  <p className="font-medium">{(data?.referral_earnings_paid_out ?? 0).toLocaleString()} {t("sum")}</p>
                </div>
              </div>
            </section>

            {/* Free Premium week claim */}
            {data?.available_weeks > 0 && (
              <section className="rounded-3xl bg-gradient-to-r from-gold/15 to-card border border-gold/40 p-4" data-testid="ref-redeem-card">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-heading text-lg flex items-center gap-2"><Crown className="w-4 h-4 text-gold-dark" /> {t("free_premium_week")}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">×{data.available_weeks} {t("claim_weeks")}</p>
                  </div>
                  <button data-testid="ref-redeem" onClick={redeem} disabled={redeeming} className="rounded-2xl bg-gold text-ink px-4 py-2.5 text-sm font-medium disabled:opacity-50">
                    {redeeming ? "..." : t("claim_weeks")}
                  </button>
                </div>
              </section>
            )}

            {/* Invite link */}
            <section className="rounded-3xl border border-border bg-card p-4 space-y-3">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">{t("ref_your_code")}</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 rounded-xl bg-muted/50 px-4 py-3 font-mono text-lg font-semibold tracking-wider text-center" data-testid="ref-code">
                  {code || "—"}
                </div>
                <button
                  data-testid="ref-copy-code"
                  onClick={() => copy(code, t("ref_your_code"))}
                  className="p-3 rounded-xl bg-primary text-white"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>
              
              {/* Custom Referral Username */}
              <div className="pt-2 border-t border-border/40">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs uppercase tracking-wider text-muted-foreground">Custom Username</p>
                  <button 
                    onClick={() => setShowUsernameModal(true)}
                    className="text-xs text-primary font-medium"
                  >
                    {usernameData?.referral_username ? "Change" : "Set"}
                  </button>
                </div>
                {usernameData?.referral_username ? (
                  <div className="flex items-center gap-2">
                    <div className="flex-1 rounded-xl bg-muted/30 px-3 py-2 text-sm font-medium">
                      @{usernameData.referral_username}
                    </div>
                    <button
                      onClick={() => copy(`@${usernameData.referral_username}`, "Username")}
                      className="p-2 rounded-xl border border-border"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">No custom username set</p>
                )}
              </div>
              
              <div>
                <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1.5">{t("ref_invite_link")}</p>
                <div className="flex items-center gap-2">
                  <div className="flex-1 rounded-xl bg-muted/30 px-3 py-2 text-xs truncate" data-testid="ref-link">{inviteLink}</div>
                  <button
                    data-testid="ref-copy-link"
                    onClick={() => copy(inviteLink, t("ref_invite_link"))}
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
                <Send className="w-4 h-4" /> {t("ref_share_btn")}
              </button>
              <a
                href={`https://t.me/share/url?url=${encodeURIComponent(inviteLink)}&text=${encodeURIComponent("FIDEM")}`}
                target="_blank"
                rel="noreferrer"
                data-testid="ref-share-tg"
                className="w-full rounded-2xl border-2 border-border py-3 font-medium flex items-center justify-center gap-2"
              >
                {t("ref_share_tg")}
              </a>
            </section>

            {/* How it works */}
            <section className="rounded-3xl border border-border bg-card p-4 space-y-3">
              <h2 className="font-heading font-semibold">{t("ref_how")}</h2>
              <div className="space-y-2 text-sm">
                <Step n="1" text={t("ref_step1") || "Yuqoridagi havolani do'stlaringizga yuboring"} />
                <Step n="2" text={t("ref_step2") || "Do'stingiz ro'yxatdan o'tib profilini to'liq tasdiqlasin"} />
                <Step n="3" text={t("ref_step3") || "Siz +10,000, do'stingiz +5,000 so'm bonus oladi"} />
                <Step n="★" gold text={t("ref_step4") || "5 ta taklif = 1 hafta bepul Premium"} />
              </div>
            </section>

            {/* Withdrawal Rules */}
            <section className="rounded-3xl border border-border bg-card p-4 space-y-3">
              <h2 className="font-heading font-semibold flex items-center gap-2">
                <Info className="w-4 h-4 text-primary" /> Withdrawal Rules
              </h2>
              <div className="space-y-2 text-xs text-muted-foreground">
                <p>• Only referral earnings can be withdrawn (not internal balance, gifts, or roses)</p>
                <p>• Minimum payout: 100,000 so'm</p>
                <p>• 12% tax withheld on withdrawals</p>
                <p>• Requires 3 paid referrals</p>
                <p>• Requires identity verification</p>
                <p>• Requires account age 30 days</p>
              </div>
            </section>
          </>
        )}
      </main>

      {/* Username Modal */}
      {showUsernameModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-card rounded-3xl p-6 w-full max-w-md space-y-4">
            <h3 className="font-heading font-semibold text-lg">Set Custom Username</h3>
            <p className="text-sm text-muted-foreground">
              {usernameData?.change_count === 0 
                ? "First change is free. Subsequent changes cost 10,000 so'm."
                : "Username change costs 10,000 so'm. 30-day cooldown between changes."
              }
            </p>
            <input
              type="text"
              placeholder="username (3-30 chars, a-z, 0-9, _)"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""))}
              className="w-full px-4 py-3 rounded-xl border border-input bg-background text-sm font-mono"
              maxLength={30}
            />
            <div className="flex gap-3">
              <button
                onClick={() => { setShowUsernameModal(false); setNewUsername(""); }}
                className="flex-1 py-3 rounded-2xl border border-border font-medium"
              >
                Cancel
              </button>
              <button
                onClick={setUsername}
                disabled={checkingUsername || !newUsername}
                className="flex-1 py-3 rounded-2xl bg-primary text-white font-medium disabled:opacity-50"
              >
                {checkingUsername ? "..." : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Step({ n, text, gold }) {
  return (
    <div className="flex gap-3">
      <span className={`w-7 h-7 rounded-full ${gold ? "bg-gold-dark" : "bg-primary"} text-white grid place-items-center text-xs shrink-0`}>{n}</span>
      <p>{text}</p>
    </div>
  );
}
