import React, { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import { ShieldCheck, Upload, CheckCircle2, XCircle, Clock, FileText, IdCard, ScanFace, Banknote, ChevronLeft } from "lucide-react";
import { useVerificationMine, QK } from "@/hooks/queries";
import { useMutation, useQueryClient } from "@tanstack/react-query";

export default function Verification() {
  const { t, user } = useApp();
  const queryClient = useQueryClient();
  const { data } = useVerificationMine();
  const anyPending = (data?.items || []).some((it) => it.status === "pending");
  // The AI usually answers within seconds: refresh while something waits.
  useEffect(() => {
    if (!anyPending) return undefined;
    const id = setInterval(() => queryClient.invalidateQueries({ queryKey: QK.verificationMine }), 5000);
    return () => clearInterval(id);
  }, [anyPending, queryClient]);
  const wasPendingSelfie = useRef(false);
  useEffect(() => {
    const selfie = (data?.items || []).find((it) => it.kind === "selfie");
    if (selfie?.status === "pending") wasPendingSelfie.current = true;
    else if (wasPendingSelfie.current && data?.verified_selfie) {
      wasPendingSelfie.current = false;
      toast.success(t("selfie_ok_toast"));
    }
  }, [data, t]);

  const kinds = [
    {
      key: "selfie",
      title: t("verify_kind_selfie_title"),
      desc: t("verify_kind_selfie_desc"),
      icon: <ScanFace className="w-5 h-5" />,
      color: "secondary",
      accept: "image/*",
    },
    {
      key: "identity",
      title: t("verify_kind_identity_title"),
      desc: t("verify_kind_identity_desc"),
      icon: <IdCard className="w-5 h-5" />,
      color: "primary",
      accept: "image/*",
    },
    {
      key: "financial",
      title: t("verify_kind_financial_title"),
      desc: t("verify_kind_financial_desc"),
      icon: <Banknote className="w-5 h-5" />,
      color: "gold",
      accept: "image/*,application/pdf",
    },
  ];

  const uploadMutation = useMutation({
    mutationFn: async ({ kind, file, note }) => {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/files/upload?purpose=private", fd, { headers: { "Content-Type": "multipart/form-data" } });
      const proof_url = `${process.env.REACT_APP_BACKEND_URL}${r.data.url}`;
      return api.post("/verification/request", { kind, note: note || "", proof_url });
    },
    onSuccess: () => {
      toast.success(t("submit_request") + " ✓");
      queryClient.invalidateQueries({ queryKey: QK.verificationMine });
    },
    onError: (e) => {
      const d = (e?.response?.data?.detail || "").toString();
      if (d === "challenge_required") toast.error(t("selfie_challenge_expired"));
      else if (e?.response?.status === 429) toast.error(t("too_many_requests"));
      else toast.error(t("error_generic"));
      queryClient.invalidateQueries({ queryKey: QK.verificationMine });
    },
  });

  const uploadAndSubmit = (kind, file, note) => uploadMutation.mutate({ kind, file, note });
  const busy = uploadMutation.isPending;

  if (!data) {
    return (
      <div className="max-w-3xl mx-auto p-4 md:p-6 space-y-6">
        <div className="h-8 bg-muted rounded animate-pulse w-1/3" />
        <div className="h-5 bg-muted rounded animate-pulse w-1/2" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-48 bg-muted rounded-2xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const verifiedMap = {
    identity: data.verified_identity,
    selfie: data.verified_selfie,
    financial: data.verified_financial,
  };

  const lastFor = (kind) => (data.items || []).find((it) => it.kind === kind);

  return (
    <div className="max-w-3xl mx-auto p-4 md:p-6 space-y-6">
      <div>
        <Link to="/me" data-testid="verify-back" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-2">
          <ChevronLeft className="w-4 h-4" /> {t("me")}
        </Link>
        <h1 className="text-2xl font-heading font-semibold flex items-center gap-2">
          <ShieldCheck className="w-6 h-6 text-secondary" /> {t("verification_title")}
        </h1>
        <p className="text-sm text-muted-foreground mt-1">{t("verification_subtitle")}</p>
        {user?.gender === "female" && !data.verified_selfie && (
          <div data-testid="verify-women-note" className="mt-3 rounded-2xl border border-secondary/30 bg-secondary/10 p-3 text-sm">
            {t("verify_women_note")}
          </div>
        )}
        <div className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-secondary/10 text-secondary border border-secondary/25 px-3 py-1 text-xs font-medium">
          <ShieldCheck className="w-3.5 h-3.5" /> {t("verify_trust_line")}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {kinds.map((k) => (
          <VerifyCard
            key={k.key}
            kind={k}
            verified={verifiedMap[k.key]}
            last={lastFor(k.key)}
            onSubmit={uploadAndSubmit}
            busy={busy}
          />
        ))}
      </div>

      <div className="rounded-2xl border border-border bg-card p-4 text-sm">
        <p className="font-medium mb-2">{t("status_legend")}</p>
        <ul className="space-y-1 text-muted-foreground text-xs">
          <li><Clock className="inline w-3 h-3 mr-1" /> {t("status_pending_desc")}</li>
          <li><CheckCircle2 className="inline w-3 h-3 mr-1 text-emerald-600" /> {t("status_approved_desc")}</li>
          <li><XCircle className="inline w-3 h-3 mr-1 text-rose-600" /> {t("status_rejected_desc")}</li>
        </ul>
      </div>
    </div>
  );
}

function VerifyCard({ kind, verified, last, onSubmit, busy }) {
  const { t, lang } = useApp();
  const inputRef = useRef(null);
  const [note, setNote] = useState("");
  const isSelfie = kind.key === "selfie";
  const [challenge, setChallenge] = useState(null);
  const [loadingCh, setLoadingCh] = useState(false);
  // Selfie: first ask the server for a random hand gesture, then open the
  // front camera. A photo stolen from someone's page can't show it.
  const startSelfie = async () => {
    setLoadingCh(true);
    try {
      const r = await api.get("/verification/selfie-challenge");
      setChallenge(r.data);
    } catch {
      toast.error(t("error_generic"));
    } finally {
      setLoadingCh(false);
    }
  };
  const gestureText = challenge ? (challenge[`text_${lang}`] || challenge.text_uz) : "";
  const onFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 8 * 1024 * 1024) { toast.error(t("verify_max_file_size")); return; }
    onSubmit(kind.key, f, note);
    if (isSelfie) setChallenge(null);
    e.target.value = "";
  };
  const status = last?.status;
  const colorMap = { primary: "border-primary/40 bg-primary/5", secondary: "border-secondary/40 bg-secondary/5", gold: "border-gold/40 bg-gold-light/30" };
  return (
    <div className={`rounded-3xl border-2 p-4 space-y-2 ${colorMap[kind.color] || "border-border"}`} data-testid={`verify-${kind.key}`}>
      <div className="flex items-center gap-2">
        <div className="w-9 h-9 rounded-xl bg-card border border-border grid place-items-center">{kind.icon}</div>
        <div className="flex-1">
          <p className="font-medium text-sm">{kind.title}</p>
          {verified ? (
            <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">
              <CheckCircle2 className="w-3 h-3" /> {t("status_approved_word")}
            </span>
          ) : status === "pending" ? (
            <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
              <Clock className="w-3 h-3" /> {t("status_pending_word")}
            </span>
          ) : status === "rejected" ? (
            <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-rose-100 text-rose-700">
              <XCircle className="w-3 h-3" /> {t("status_rejected_word")}
            </span>
          ) : (
            <span className="text-[11px] text-muted-foreground">—</span>
          )}
        </div>
      </div>
      <p className="text-xs text-muted-foreground">{kind.desc}</p>
      {status === "rejected" && last?.rejection_reason && (
        <p className="text-xs text-rose-700 bg-rose-50 rounded-lg p-2">{last.rejection_reason}</p>
      )}
      {!verified && isSelfie && status !== "pending" && (
        <>
          {challenge ? (
            <div data-testid="selfie-gesture" className="rounded-2xl bg-card border-2 border-secondary p-3 text-center space-y-1">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{t("selfie_do_this")}</p>
              <p className="text-base font-semibold">✋ {gestureText}</p>
              <p className="text-[11px] text-muted-foreground">{t("selfie_face_visible")}</p>
            </div>
          ) : null}
          <input
            ref={inputRef}
            data-testid="verify-file-selfie"
            type="file"
            accept="image/*"
            capture="user"
            className="hidden"
            onChange={onFile}
          />
          <button
            data-testid="verify-upload-selfie"
            disabled={busy || loadingCh}
            onClick={() => (challenge ? inputRef.current?.click() : startSelfie())}
            className="w-full inline-flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-primary text-white text-sm font-medium disabled:opacity-50"
          >
            <ScanFace className="w-4 h-4" />
            {busy ? "..." : challenge ? t("selfie_take_photo") : status === "rejected" ? t("retry_word") : t("selfie_start")}
          </button>
        </>
      )}
      {!verified && isSelfie && status === "pending" && (
        <p className="text-xs text-amber-700 bg-amber-50 rounded-lg p-2">{t("selfie_checking")}</p>
      )}
      {!verified && !isSelfie && (
        <>
          <input
            data-testid={`verify-note-${kind.key}`}
            placeholder={t("optional_word")}
            className="w-full text-xs px-3 py-2 rounded-lg border border-input bg-background"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <input
            ref={inputRef}
            data-testid={`verify-file-${kind.key}`}
            type="file"
            accept={kind.accept}
            className="hidden"
            onChange={onFile}
          />
          <button
            data-testid={`verify-upload-${kind.key}`}
            disabled={busy || status === "pending"}
            onClick={() => inputRef.current?.click()}
            className="w-full inline-flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-primary text-white text-sm font-medium disabled:opacity-50"
          >
            <Upload className="w-4 h-4" />
            {status === "pending" ? t("status_pending_word") : status === "rejected" ? t("retry_word") : t("verify_upload_btn")}
          </button>
          {last?.proof_url && (
            <a href={last.proof_url} target="_blank" rel="noreferrer" className="text-[11px] text-foreground inline-flex items-center gap-1">
              <FileText className="w-3 h-3" /> {t("verify_view_proof")}
            </a>
          )}
        </>
      )}
    </div>
  );
}
