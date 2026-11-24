import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Mail } from "lucide-react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";

// "Kirish usuli": attach an email + password to the account (people who joined
// through Telegram have none, so a phone app could never sign them back in), or
// confirm the email they registered with. A 6-digit code goes to the address.
export default function EmailLogin() {
  const { t, user, refresh } = useApp();
  const [status, setStatus] = useState(null);       // { enabled, password_min }
  const [email, setEmail] = useState(user?.email || "");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/auth/email/status").then((r) => setStatus(r.data)).catch(() => setStatus({ enabled: false }));
  }, []);

  const verified = !!(user?.email && user?.email_verified && user?.has_password);
  const needsPassword = !user?.has_password;

  const errText = (e) => {
    const d = (e?.response?.data?.detail || "").toString();
    return ({
      weak_password: t("auth_weak_password").replace("{n}", status?.password_min || 8),
      invalid_code: t("auth_invalid_code"),
      email_taken: t("acc_email_taken"),
      email_unavailable: t("auth_email_unavailable"),
      email_send_failed: t("auth_email_unavailable"),
      email_already_set: t("acc_email_already_set"),
      account_blocked: t("error_generic"),
    })[d] || t("error_generic");
  };

  const sendCode = async () => {
    if (busy || !email.trim()) return;
    setBusy(true);
    try {
      await api.post("/auth/email/start", { email: email.trim() });
      setSent(true);
      toast.success(t("auth_code_sent"));
    } catch (e) { toast.error(errText(e)); } finally { setBusy(false); }
  };

  const confirm = async () => {
    if (busy || code.trim().length < 6) return;
    setBusy(true);
    try {
      const r = await api.post("/auth/email/confirm", { code: code.trim(), password: needsPassword ? password : undefined });
      toast.success(t("acc_email_done"));
      setSent(false); setCode(""); setPassword("");
      await refresh(r.data.user);
    } catch (e) { toast.error(errText(e)); } finally { setBusy(false); }
  };

  return (
    <div className="rounded-3xl bg-card border border-border p-4 space-y-3" data-testid="email-login">
      <p className="text-xs uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
        <Mail className="w-3.5 h-3.5" /> {t("acc_login_title")}
      </p>
      {verified ? (
        <p className="text-sm" data-testid="email-login-done">✅ {user.email} · {t("acc_email_verified")}</p>
      ) : status && !status.enabled ? (
        <p className="text-sm text-muted-foreground" data-testid="email-login-unavailable">{t("auth_email_unavailable")}</p>
      ) : (
        <>
          <p className="text-sm text-muted-foreground leading-snug">
            {user?.email ? t("acc_email_unverified_hint") : t("acc_login_hint")}
          </p>
          <input
            data-testid="email-login-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={!!user?.email || sent}
            placeholder={t("email")}
            className="input"
          />
          {!sent ? (
            <button data-testid="email-login-send" onClick={sendCode} disabled={busy || !email.trim()} className="btn-primary">
              {t("auth_send_code")}
            </button>
          ) : (
            <>
              <input
                data-testid="email-login-code"
                inputMode="numeric"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                placeholder={t("auth_code")}
                className="input tracking-[0.4em] text-center"
              />
              {needsPassword && (
                <input
                  data-testid="email-login-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={t("auth_new_password")}
                  className="input"
                />
              )}
              <button data-testid="email-login-confirm" onClick={confirm} disabled={busy || code.length < 6 || (needsPassword && !password)} className="btn-primary">
                {t("acc_email_confirm")}
              </button>
            </>
          )}
        </>
      )}
    </div>
  );
}
