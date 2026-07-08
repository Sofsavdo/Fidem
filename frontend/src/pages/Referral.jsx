import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, Copy, Send, Users, Gift, Crown } from "lucide-react";
import { toast } from "sonner";
import { useApp } from "@/contexts/AppContext";
import { useReferral, useReferralUsername, QK } from "@/hooks/queries";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export default function Referral() {
  const { t } = useApp();
  const queryClient = useQueryClient();
  const [showUsernameModal, setShowUsernameModal] = useState(false);
  const [newUsername, setNewUsername] = useState("");

  const { data, isLoading } = useReferral();
  const { data: usernameData } = useReferralUsername();

  const setUsernameMutation = useMutation({
    mutationFn: (username) => api.post("/referral/username/set", { username }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.referralUsername });
      toast.success("Username updated successfully");
      setShowUsernameModal(false);
      setNewUsername("");
    },
    onError: (e) => toast.error(e.response?.data?.detail || "Failed to set username"),
  });

  const setUsername = () => {
    if (!newUsername || newUsername.length < 3 || newUsername.length > 30) {
      toast.error("Username must be 3-30 characters");
      return;
    }
    setUsernameMutation.mutate(newUsername);
  };

  const code = data?.code || "";
  const inviteLink = data?.link || (code ? `https://t.me/Fidem_Appbot?start=${code}` : "");

  const copy = (text, label) => {
    navigator.clipboard.writeText(text).then(() => toast.success(`${label} ${t("copied")}`)).catch(() => toast.error(t("error")));
  };

  const share = () => {
    const txt = `🌹 FIDEM\n\n${inviteLink}`;
    if (navigator.share) {
      navigator.share({ title: "FIDEM", text: txt }).catch(() => {});
    } else {
      copy(txt, t("share"));
    }
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
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span title="Referral linkingizni do'stingizga yuboring • Do'stingiz ro'yxatdan o'tadi • Do'stingiz birinchi pullik tarifni sotib olganda sizga referral mukofoti yoziladi" className="cursor-help">ℹ️</span>
          <span>{t("ref_how_it_works")}</span>
        </div>

        <section className="text-center space-y-3">
          <div className="text-6xl">🎁</div>
          <h1 className="text-2xl font-heading font-bold">{t("ref_subtitle")}</h1>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            Do'stingiz birinchi pullik tarifni sotib olganda sizga referral mukofoti yoziladi
          </p>
        </section>

        {isLoading ? (
          <div className="text-center text-sm text-muted-foreground py-8">{t("loading")}</div>
        ) : (
          <>
            {/* Stats */}
            <section className="grid grid-cols-2 gap-2">
              <div className="rounded-2xl border border-border bg-card p-3 text-center" data-testid="ref-stat-invites">
                <Users className="w-5 h-5 mx-auto text-foreground mb-1" />
                <p className="text-xl font-heading font-bold">{data?.invited_count ?? 0}</p>
                <p className="text-[11px] text-muted-foreground">{t("ref_invites")}</p>
              </div>
              <div className="rounded-2xl border border-border bg-card p-3 text-center" data-testid="ref-stat-paid">
                <Crown className="w-5 h-5 mx-auto text-gold-dark mb-1" />
                <p className="text-xl font-heading font-bold">{data?.paid_referrals ?? 0}</p>
                <p className="text-[11px] text-muted-foreground">{t("ref_paid_referrals")}</p>
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
                  <p className="font-medium text-foreground">{(data?.referral_earnings_withdrawable ?? 0).toLocaleString()} {t("sum")}</p>
                </div>
                <div className="rounded-xl bg-muted/30 p-3">
                  <p className="text-muted-foreground text-xs">{t("referral_earnings_paid_out")}</p>
                  <p className="font-medium">{(data?.referral_earnings_paid_out ?? 0).toLocaleString()} {t("sum")}</p>
                </div>
              </div>
            </section>

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
                    className="text-xs text-foreground font-medium"
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
                <Step n="1" text="Referral linkingizni do'stingizga yuboring" />
                <Step n="2" text="Do'stingiz ro'yxatdan o'tadi" />
                <Step n="3" text="Do'stingiz birinchi marta pullik tarif sotib olsa, sizga referral mukofoti yoziladi" />
                <Step n="4" text="Mukofot avval pending bo'ladi. Tekshiruv/hold tugagach withdrawable bo'ladi" />
              </div>
            </section>

            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span title="Minimal yechib olish: 100,000 • Soliq: 12% • Talab: 3 ta to'langan tavsiya" className="cursor-help">ℹ️</span>
              <span>{t("withdraw_rules")}</span>
            </div>
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
                disabled={setUsernameMutation.isPending || !newUsername}
                className="flex-1 py-3 rounded-2xl bg-primary text-white font-medium disabled:opacity-50"
              >
                {setUsernameMutation.isPending ? "..." : "Save"}
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
