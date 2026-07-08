import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, Copy, Send, Users, Crown, TrendingUp, Wallet } from "lucide-react";
import { toast } from "sonner";
import { useApp } from "@/contexts/AppContext";
import { useReferral, useReferralUsername, QK } from "@/hooks/queries";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { Skeleton, SectionLabel } from "@/components/kit";

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
      toast.success(t("ref_username_updated"));
      setShowUsernameModal(false);
      setNewUsername("");
    },
    onError: (e) => toast.error(e.response?.data?.detail || t("error_generic")),
  });

  const setUsername = () => {
    if (!newUsername || newUsername.length < 3 || newUsername.length > 30) {
      toast.error(t("ref_username_len_err"));
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

  const earnings = [
    { key: "referral_earnings_withdrawable", value: data?.referral_earnings_withdrawable, highlight: true },
    { key: "referral_earnings_pending", value: data?.referral_earnings_pending },
    { key: "referral_earnings_approved", value: data?.referral_earnings_approved },
    { key: "referral_earnings_paid_out", value: data?.referral_earnings_paid_out },
  ];

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <Link to="/me" className="p-2 -ml-2 rounded-full hover:bg-muted" data-testid="ref-back">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <span className="font-heading font-semibold text-lg">{t("ref_title")}</span>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-5 space-y-4">
        {/* Hero — compact, premium */}
        <section className="rounded-3xl bg-gradient-to-br from-secondary/12 via-card to-gold-light/20 border border-secondary/25 p-5 text-center">
          <div className="w-12 h-12 mx-auto rounded-2xl bg-secondary/15 grid place-items-center">
            <TrendingUp className="w-6 h-6 text-secondary" />
          </div>
          <h1 className="text-xl font-heading font-semibold mt-3">{t("ref_subtitle")}</h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto leading-snug">{t("ref_hero_desc")}</p>
        </section>

        {isLoading ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-2">
              <Skeleton className="h-20 rounded-2xl" /><Skeleton className="h-20 rounded-2xl" />
            </div>
            <Skeleton className="h-40 rounded-3xl" />
            <Skeleton className="h-52 rounded-3xl" />
          </div>
        ) : (
          <>
            {/* Stats */}
            <section className="grid grid-cols-2 gap-2">
              <div className="rounded-2xl border border-border bg-card p-3 text-center" data-testid="ref-stat-invites">
                <Users className="w-5 h-5 mx-auto text-secondary mb-1" />
                <p className="text-xl font-heading font-semibold tabular-nums">{data?.invited_count ?? 0}</p>
                <p className="text-[11px] text-muted-foreground">{t("ref_invites")}</p>
              </div>
              <div className="rounded-2xl border border-border bg-card p-3 text-center" data-testid="ref-stat-paid">
                <Crown className="w-5 h-5 mx-auto text-gold-dark mb-1" />
                <p className="text-xl font-heading font-semibold tabular-nums">{data?.paid_referrals ?? 0}</p>
                <p className="text-[11px] text-muted-foreground">{t("ref_paid_referrals")}</p>
              </div>
            </section>

            {/* Earnings breakdown — withdrawable highlighted */}
            <section className="rounded-3xl border border-border bg-card p-4">
              <div className="flex items-center justify-between mb-3">
                <SectionLabel>{t("ref_earnings_label")}</SectionLabel>
                <Link to="/withdrawals" data-testid="ref-to-withdrawals" className="text-xs font-semibold text-primary inline-flex items-center gap-1">
                  <Wallet className="w-3.5 h-3.5" /> {t("withdraw_cta")}
                </Link>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                {earnings.map((e) => (
                  <div
                    key={e.key}
                    className={`rounded-2xl p-3 border ${e.highlight ? "bg-secondary/10 border-secondary/30" : "bg-muted/30 border-transparent"}`}
                  >
                    <p className="text-muted-foreground text-[11px] leading-tight">{t(e.key)}</p>
                    <p className={`font-semibold tabular-nums mt-0.5 ${e.highlight ? "text-secondary" : ""}`}>
                      {(e.value ?? 0).toLocaleString()} {t("sum")}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            {/* Invite code + link */}
            <section className="rounded-3xl border border-border bg-card p-4 space-y-3">
              <SectionLabel>{t("ref_your_code")}</SectionLabel>
              <div className="flex items-center gap-2">
                <div className="flex-1 rounded-2xl bg-muted/50 px-4 py-3 font-mono text-lg font-semibold tracking-[0.15em] text-center" data-testid="ref-code">
                  {code || "—"}
                </div>
                <button data-testid="ref-copy-code" onClick={() => copy(code, t("ref_your_code"))} className="p-3 rounded-2xl bg-primary text-white active:scale-95 transition">
                  <Copy className="w-4 h-4" />
                </button>
              </div>

              {/* Custom referral username */}
              <div className="pt-1">
                <div className="flex items-center justify-between mb-2">
                  <SectionLabel>{t("ref_custom_username")}</SectionLabel>
                  <button data-testid="ref-username-edit" onClick={() => setShowUsernameModal(true)} className="text-xs text-primary font-semibold">
                    {usernameData?.referral_username ? t("ref_username_change") : t("ref_username_set")}
                  </button>
                </div>
                {usernameData?.referral_username ? (
                  <div className="flex items-center gap-2">
                    <div className="flex-1 rounded-xl bg-muted/30 px-3 py-2 text-sm font-medium">@{usernameData.referral_username}</div>
                    <button onClick={() => copy(`@${usernameData.referral_username}`, t("ref_custom_username"))} className="p-2 rounded-xl border border-border active:scale-95 transition">
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">{t("ref_username_none")}</p>
                )}
              </div>

              <div>
                <SectionLabel className="mb-1.5">{t("ref_invite_link")}</SectionLabel>
                <div className="flex items-center gap-2">
                  <div className="flex-1 rounded-xl bg-muted/30 px-3 py-2 text-xs truncate" data-testid="ref-link">{inviteLink}</div>
                  <button data-testid="ref-copy-link" onClick={() => copy(inviteLink, t("ref_invite_link"))} className="p-2 rounded-xl border border-border active:scale-95 transition">
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <button data-testid="ref-share" onClick={share} className="btn-primary">
                <Send className="w-4 h-4" /> {t("ref_share_btn")}
              </button>
              <a
                href={`https://t.me/share/url?url=${encodeURIComponent(inviteLink)}&text=${encodeURIComponent("FIDEM")}`}
                target="_blank"
                rel="noreferrer"
                data-testid="ref-share-tg"
                className="w-full rounded-2xl border border-border py-3 font-medium flex items-center justify-center gap-2 active:scale-[0.99] transition"
              >
                {t("ref_share_tg")}
              </a>
            </section>

            {/* How it works */}
            <section className="rounded-3xl border border-border bg-card p-4 space-y-3">
              <SectionLabel>{t("ref_how")}</SectionLabel>
              <div className="space-y-2.5 text-sm">
                {[t("ref_step_1"), t("ref_step_2"), t("ref_step_3"), t("ref_step_4")].map((txt, i) => (
                  <div key={i} className="flex gap-3">
                    <span className="w-6 h-6 rounded-full bg-secondary/12 text-secondary grid place-items-center text-xs font-semibold shrink-0">{i + 1}</span>
                    <p className="leading-snug pt-0.5">{txt}</p>
                  </div>
                ))}
              </div>
              <p className="text-[11px] text-muted-foreground pt-2 border-t border-border/40 leading-snug">
                {t("withdraw_rules")}
              </p>
            </section>
          </>
        )}
      </main>

      {/* Username modal */}
      {showUsernameModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm" onClick={() => setShowUsernameModal(false)}>
          <div className="bg-card rounded-3xl p-6 w-full max-w-md space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-heading font-semibold text-lg">{t("ref_username_modal_title")}</h3>
            <p className="text-sm text-muted-foreground">
              {usernameData?.change_count === 0 ? t("ref_username_first_free") : t("ref_username_next_paid")}
            </p>
            <input
              type="text"
              placeholder="username (a-z, 0-9, _)"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""))}
              className="input font-mono"
              maxLength={30}
            />
            <div className="flex gap-3">
              <button onClick={() => { setShowUsernameModal(false); setNewUsername(""); }} className="flex-1 py-3 rounded-2xl border border-border font-medium">
                {t("common_cancel")}
              </button>
              <button onClick={setUsername} disabled={setUsernameMutation.isPending || !newUsername} className="flex-1 py-3 rounded-2xl bg-primary text-white font-medium disabled:opacity-50">
                {setUsernameMutation.isPending ? "..." : t("common_save")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
