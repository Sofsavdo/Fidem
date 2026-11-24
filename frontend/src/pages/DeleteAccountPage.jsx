import React from "react";
import { Link } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import DeleteAccount from "@/components/DeleteAccount";
import { SUPPORT_URL } from "@/lib/support";

// The public "how do I delete my account" page (store listings link here).
// Anyone can read it; the form itself needs the person to be signed in.
export default function DeleteAccountPage() {
  const { t, user } = useApp();
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <Link to={user ? "/me/settings" : "/welcome"} className="p-2 -ml-2 rounded-full hover:bg-muted">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <span className="font-heading font-semibold text-lg">{t("acc_delete_title")}</span>
      </header>
      <main className="max-w-2xl mx-auto px-5 py-6 space-y-5 pb-16" data-testid="delete-account-page">
        <p className="text-sm text-muted-foreground leading-relaxed">{t("acc_delete_page_intro")}</p>
        <ol className="list-decimal pl-5 text-sm space-y-1.5">
          <li>{t("acc_delete_step_1")}</li>
          <li>{t("acc_delete_step_2")}</li>
          <li>{t("acc_delete_step_3")}</li>
        </ol>
        <p className="text-sm text-muted-foreground leading-relaxed">{t("acc_delete_what_stays")}</p>
        {user ? (
          <DeleteAccount startOpen />
        ) : (
          <Link to="/auth" data-testid="delete-account-signin" className="btn-primary inline-flex">{t("login")}</Link>
        )}
        <p className="text-sm">
          {t("acc_delete_help")} <a className="text-primary underline" href={SUPPORT_URL} target="_blank" rel="noreferrer">{SUPPORT_URL.replace("https://", "")}</a>
        </p>
      </main>
    </div>
  );
}
