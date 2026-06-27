import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { Sparkles, ArrowRight, Award } from "lucide-react";
import { toast } from "sonner";

export default function Personality() {
  const { t, lang, refresh } = useApp();
  const nav = useNavigate();
  const [questions, setQuestions] = useState([]);
  const [traitLabels, setTraitLabels] = useState({});
  const [answers, setAnswers] = useState({});
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    api.get(`/personality/questions?lang=${lang}`).then((r) => {
      setQuestions(r.data.questions || []);
      setTraitLabels(r.data.trait_labels || {});
    });
    api.get("/personality/mine").then((r) => {
      if (r.data?.scores && Object.keys(r.data.scores).length > 0) {
        setResult({ scores: r.data.scores, completed_at: r.data.completed_at });
      }
    });
  }, [lang]);

  const setAns = (qid, value) => {
    setAnswers((a) => ({ ...a, [qid]: value }));
    if (step < questions.length - 1) setTimeout(() => setStep((s) => s + 1), 120);
  };

  const submit = async () => {
    setSubmitting(true);
    try {
      const r = await api.post("/personality/submit", answers);
      setResult({ scores: r.data.scores, bonus: r.data.bonus });
      toast.success(`Test tugatildi! +${r.data.bonus} so'm bonus 🎉`);
      refresh();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Xato");
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return (
      <div className="p-5 max-w-2xl mx-auto" data-testid="personality-result">
        <div className="text-center mb-6">
          <div className="w-16 h-16 rounded-3xl bg-secondary text-white grid place-items-center mx-auto mb-3">
            <Award className="w-7 h-7" />
          </div>
          <h1 className="font-heading text-2xl font-semibold">Shaxsiyat profilingiz</h1>
          <p className="text-sm text-muted-foreground mt-1">Big 5 / OCEAN modeli asosida</p>
        </div>
        <div className="space-y-3">
          {Object.entries(result.scores).map(([trait, score]) => (
            <div key={trait} className="rounded-2xl bg-card border border-border p-4">
              <div className="flex justify-between items-center mb-2">
                <p className="font-medium">{traitLabels[trait] || trait}</p>
                <p className="text-2xl font-heading font-semibold text-secondary">{score}</p>
              </div>
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-secondary to-primary transition-all" style={{ width: `${score}%` }} />
              </div>
            </div>
          ))}
        </div>
        <div className="mt-6 rounded-2xl bg-secondary/5 border-2 border-secondary/30 p-4">
          <p className="text-sm leading-relaxed">
            <Sparkles className="w-4 h-4 inline mr-1 text-secondary" />
            Profilingiz endi nomzodlar bilan moslik tahlilida ishlatiladi. Har bir profilda batafsil AI-hisobotni ko'rishingiz mumkin.
          </p>
        </div>
        <button onClick={() => nav("/")} className="mt-6 w-full rounded-2xl bg-primary text-white py-3 font-medium">
          Nomzodlarga qaytish
        </button>
        <button onClick={() => { setResult(null); setAnswers({}); setStep(0); }} className="mt-2 w-full rounded-2xl border border-border py-2.5 text-sm text-muted-foreground">
          Qayta topshirish
        </button>
      </div>
    );
  }

  if (questions.length === 0) return <div className="p-6 text-center text-muted-foreground">Yuklanmoqda…</div>;

  const q = questions[step];
  const progress = Math.round(((step + (answers[q.id] ? 1 : 0)) / questions.length) * 100);
  const allAnswered = questions.every((qq) => answers[qq.id]);

  return (
    <div className="p-5 max-w-xl mx-auto" data-testid="personality-quiz">
      <div className="text-center mb-4">
        <h1 className="font-heading text-2xl font-semibold">Shaxsiyat testi</h1>
        <p className="text-xs text-muted-foreground mt-1">{step + 1} / {questions.length}</p>
      </div>
      <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden mb-6">
        <div className="h-full bg-primary transition-all" style={{ width: `${progress}%` }} />
      </div>

      <div className="rounded-3xl bg-card border border-border p-5 shadow-soft" data-testid={`q-${q.id}`}>
        <p className="text-lg font-medium leading-relaxed mb-5">{q.question}</p>
        <div className="space-y-2">
          {q.scale.map((opt) => (
            <button
              key={opt.value}
              data-testid={`ans-${q.id}-${opt.value}`}
              onClick={() => setAns(q.id, opt.value)}
              className={`w-full rounded-2xl border px-4 py-3 text-left text-sm transition ${
                answers[q.id] === opt.value
                  ? "border-primary bg-primary/5 text-primary font-medium"
                  : "border-border hover:bg-muted"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-2 mt-4">
        <button onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0} className="flex-1 rounded-2xl border border-border py-3 text-sm disabled:opacity-40">
          Orqaga
        </button>
        {step < questions.length - 1 ? (
          <button onClick={() => setStep((s) => Math.min(questions.length - 1, s + 1))} className="flex-1 rounded-2xl bg-primary text-white py-3 text-sm font-medium">
            Keyingi <ArrowRight className="w-4 h-4 inline ml-1" />
          </button>
        ) : (
          <button
            data-testid="personality-submit"
            onClick={submit}
            disabled={!allAnswered || submitting}
            className="flex-1 rounded-2xl bg-secondary text-white py-3 text-sm font-medium disabled:opacity-50"
          >
            {submitting ? "Yuborilmoqda…" : "Yakunlash"}
          </button>
        )}
      </div>
    </div>
  );
}
