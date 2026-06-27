import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { Mic, Square, Trash2, Pen, Save } from "lucide-react";

export default function Prompts() {
  const [library, setLibrary] = useState([]);
  const [mine, setMine] = useState([]);
  const [saving, setSaving] = useState(false);
  const nav = useNavigate();

  useEffect(() => {
    api.get("/prompts/library?lang=uz").then((r) => setLibrary(r.data || []));
    api.get("/prompts/mine").then((r) => setMine(r.data || []));
  }, []);

  const addPrompt = (libItem) => {
    if (mine.length >= 3) {
      toast.error("Maksimal 3 ta prompt");
      return;
    }
    if (mine.find((p) => p.id === libItem.id)) {
      toast.info("Bu prompt allaqachon qo'shilgan");
      return;
    }
    setMine([...mine, { id: libItem.id, text: libItem.text, answer: "", kind: "text" }]);
  };

  const removePrompt = (id) => setMine(mine.filter((p) => p.id !== id));

  const updateAnswer = (id, answer) => setMine(mine.map((p) => p.id === id ? { ...p, answer } : p));

  const setVoice = (id, voice_url, duration_sec) => setMine(mine.map((p) => p.id === id ? { ...p, kind: "voice", voice_url, duration_sec } : p));
  const setText = (id) => setMine(mine.map((p) => p.id === id ? { ...p, kind: "text", voice_url: null } : p));

  const save = async () => {
    setSaving(true);
    try {
      const payload = mine.map((p) => ({ id: p.id, answer: p.answer, kind: p.kind, voice_url: p.voice_url, duration_sec: p.duration_sec || 0 }));
      await api.post("/prompts/save", payload);
      toast.success("Saqlandi");
    } catch (e) {
      toast.error("Xato");
    } finally { setSaving(false); }
  };

  return (
    <div className="p-5 max-w-3xl mx-auto pb-24" data-testid="prompts-page">
      <h1 className="font-heading text-2xl font-semibold mb-1">Profil promptlari</h1>
      <p className="text-sm text-muted-foreground mb-5">3 ta savolni tanlang va o'z so'zingiz bilan javob bering (yoki ovoz orqali). Profilingiz boshqalarga jonli ko'rinadi.</p>

      <h2 className="font-medium text-sm text-muted-foreground uppercase tracking-wider mb-2">Mening promptlarim ({mine.length}/3)</h2>
      <div className="space-y-3 mb-6">
        {mine.length === 0 && <p className="rounded-2xl border-2 border-dashed border-border p-4 text-sm text-muted-foreground text-center">Quyidan birorta savol tanlang →</p>}
        {mine.map((p) => (
          <div key={p.id} className="rounded-2xl bg-card border border-border p-4">
            <div className="flex items-start justify-between gap-2 mb-2">
              <p className="font-medium">{p.text || library.find((l) => l.id === p.id)?.text}</p>
              <button data-testid={`remove-${p.id}`} onClick={() => removePrompt(p.id)} className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground"><Trash2 className="w-4 h-4" /></button>
            </div>
            <div className="flex gap-2 mb-2">
              <button onClick={() => setText(p.id)} className={`text-xs rounded-full px-3 py-1 ${p.kind === "text" ? "bg-primary text-white" : "bg-muted"}`}><Pen className="w-3 h-3 inline mr-1" /> Matn</button>
              <VoiceRecorder onUploaded={(url, dur) => setVoice(p.id, url, dur)} kind={p.kind} />
            </div>
            {p.kind === "text" ? (
              <textarea
                data-testid={`answer-${p.id}`}
                value={p.answer}
                onChange={(e) => updateAnswer(p.id, e.target.value)}
                placeholder="Javobingizni shu yerga yozing…"
                rows={3}
                maxLength={500}
                className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
              />
            ) : p.voice_url ? (
              <audio controls src={p.voice_url} className="w-full mt-2" />
            ) : (
              <p className="text-xs text-muted-foreground">Ovoz yozishni boshlash uchun yuqoridagi tugmani bosing</p>
            )}
          </div>
        ))}
      </div>

      <h2 className="font-medium text-sm text-muted-foreground uppercase tracking-wider mb-2">Kutubxona</h2>
      <div className="grid sm:grid-cols-2 gap-2 mb-6">
        {library.filter((l) => !mine.find((m) => m.id === l.id)).map((l) => (
          <button key={l.id} data-testid={`add-${l.id}`} onClick={() => addPrompt(l)} className="rounded-2xl border border-border bg-card hover:border-primary p-3 text-left text-sm transition">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{l.category}</p>
            <p className="mt-0.5">{l.text}</p>
          </button>
        ))}
      </div>

      <div className="sticky bottom-24 flex gap-2">
        <button onClick={() => nav("/me")} className="flex-1 rounded-2xl border border-border py-3 text-sm">Bekor qilish</button>
        <button data-testid="save-prompts" onClick={save} disabled={saving || mine.length === 0} className="flex-1 rounded-2xl bg-primary text-white py-3 text-sm font-medium disabled:opacity-50 inline-flex items-center justify-center gap-2">
          <Save className="w-4 h-4" /> {saving ? "Saqlanmoqda…" : "Saqlash"}
        </button>
      </div>
    </div>
  );
}

// ----- Voice Recorder -----
function VoiceRecorder({ onUploaded, kind }) {
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [startTime, setStartTime] = useState(null);

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
      const localChunks = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) localChunks.push(e.data); };
      mr.onstop = async () => {
        const blob = new Blob(localChunks, { type: "audio/webm" });
        const dur = Math.round((Date.now() - startTime) / 1000);
        if (dur > 60) { toast.error("60 soniyadan oshmasligi kerak"); return; }
        setUploading(true);
        try {
          const fd = new FormData();
          fd.append("file", blob, "voice.webm");
          const r = await api.post("/prompts/voice-upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
          const url = `${process.env.REACT_APP_BACKEND_URL}${r.data.url}`;
          onUploaded(url, dur);
          toast.success("Ovoz yuklandi");
        } catch (e) { toast.error("Yuklash xatosi"); } finally { setUploading(false); }
        stream.getTracks().forEach((t) => t.stop());
      };
      mr.start();
      setMediaRecorder(mr);
      setStartTime(Date.now());
      setRecording(true);
      setChunks([]);
      setTimeout(() => { if (mr.state === "recording") { mr.stop(); setRecording(false); } }, 60000);
    } catch (e) {
      toast.error("Mikrofon ruxsati kerak");
    }
  };

  const stop = () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      setRecording(false);
    }
  };

  return (
    <button onClick={recording ? stop : start} disabled={uploading} className={`text-xs rounded-full px-3 py-1 inline-flex items-center gap-1 ${kind === "voice" ? "bg-primary text-white" : "bg-muted"} ${recording ? "animate-pulse bg-red-500 text-white" : ""}`}>
      {recording ? <><Square className="w-3 h-3" /> To'xtatish</> : <><Mic className="w-3 h-3" /> {uploading ? "Yuklanmoqda…" : "Ovoz"}</>}
    </button>
  );
}
