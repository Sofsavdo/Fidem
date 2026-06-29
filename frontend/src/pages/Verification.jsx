import React, { useEffect, useState, useRef } from "react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import { ShieldCheck, Upload, CheckCircle2, XCircle, Clock, FileText, IdCard, ScanFace, Banknote } from "lucide-react";

export default function Verification() {
  const { t } = useApp();
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);

  const kinds = [
    {
      key: "identity",
      title: t("verify_kind_identity_title"),
      desc: t("verify_kind_identity_desc"),
      icon: <IdCard className="w-5 h-5" />,
      color: "primary",
      accept: "image/*",
    },
    {
      key: "selfie",
      title: t("verify_kind_selfie_title"),
      desc: t("verify_kind_selfie_desc"),
      icon: <ScanFace className="w-5 h-5" />,
      color: "secondary",
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

  const load = () => api.get("/verification/mine").then((r) => setData(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const uploadAndSubmit = async (kind, file, note) => {
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/files/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      const proof_url = `${process.env.REACT_APP_BACKEND_URL}${r.data.url}`;
      await api.post("/verification/request", { kind, note: note || "", proof_url });
      toast.success(t("submit_request") + " ✓");
      load();
    } catch (e) {
      toast.error(t("error_generic"));
    } finally { setBusy(false); }
  };

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
        <h1 className="text-2xl font-heading font-semibold flex items-center gap-2">
          <ShieldCheck className="w-6 h-6 text-primary" /> {t("verification_title")}
        </h1>
        <p className="text-sm text-muted-foreground mt-1">{t("verification_subtitle")}</p>
        <p className="text-xs text-secondary mt-2">📋 Roadmap: Live camera selfie + face comparison coming soon</p>
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
  const { t } = useApp();
  const inputRef = useRef(null);
  const [note, setNote] = useState("");
  const onFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 8 * 1024 * 1024) { toast.error(t("verify_max_file_size")); return; }
    onSubmit(kind.key, f, note);
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
      {!verified && (
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
            <a href={last.proof_url} target="_blank" rel="noreferrer" className="text-[11px] text-primary inline-flex items-center gap-1">
              <FileText className="w-3 h-3" /> {t("verify_view_proof")}
            </a>
          )}
        </>
      )}
    </div>
  );
}
