import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { ArrowLeft, Sparkles, Check } from "lucide-react";
import { toast } from "sonner";

export default function Quiz() {
  const { t, lang } = useApp();
  const nav = useNavigate();
  const [qs, setQs] = useState([]);
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get("/quiz/questions").then((r) => setQs(r.data || []));
  }, []);

  const submit = async () => {
    if (Object.keys(answers).length < qs.length) {
      toast.error("Hamma savollarga javob bering");
      return;
    }
    setSubmitting(true);
    try {
      const r = await api.post("/quiz/submit", answers);
      toast.success(`+${r.data.bonus} so'm bonus · Moslik aniqligi oshdi`);
      nav("/");
    } catch (e) {
      toast.error("Xato");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="px-4 md:px-8 pt-6 pb-8 space-y-5" data-testid="quiz-page">
      <div className="flex items-center gap-3">
        <Link to="/me" className="p-2 rounded-full hover:bg-muted" data-testid="quiz-back">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <h1 className="font-heading text-2xl md:text-3xl font-semibold tracking-tight">{t("quiz_title")}</h1>
          <p className="text-xs text-muted-foreground">
            <Sparkles className="inline w-3 h-3 mr-1 text-gold-dark" />
            {t("quiz_subtitle")} · +100 {t("coins_word")}
          </p>
        </div>
      </div>

      {qs.length === 0 && <p className="text-muted-foreground">{t("loading")}</p>}

      <div className="space-y-4">
        {qs.map((q, i) => {
          const qText = q[`q_${lang}`] || q.q_uz;
          return (
            <div key={q.id} className="rounded-3xl bg-card border border-border p-4 md:p-5" data-testid={`quiz-q-${q.id}`}>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">{i + 1} / {qs.length}</p>
              <p className="font-medium text-base mt-1">{qText}</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-3">
                {q.options.map((opt) => {
                  const selected = answers[q.id] === opt.key;
                  const label = opt[lang] || opt.uz;
                  return (
                    <button
                      key={opt.key}
                      data-testid={`quiz-opt-${q.id}-${opt.key}`}
                      onClick={() => setAnswers({ ...answers, [q.id]: opt.key })}
                      className={`rounded-2xl border p-3 text-left text-sm transition ${
                        selected ? "bg-primary text-white border-primary" : "bg-card border-border hover:border-foreground/30"
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        {selected && <Check className="w-3.5 h-3.5" />}
                        {label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      <button
        data-testid="quiz-submit"
        onClick={submit}
        disabled={submitting || qs.length === 0}
        className="w-full md:w-auto md:px-12 rounded-2xl bg-primary text-white py-3 font-medium disabled:opacity-50"
      >
        {submitting ? "..." : "Yakunlash"}
      </button>
    </div>
  );
}
