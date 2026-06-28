import React, { useEffect, useRef, useState } from "react";
import { Mic, Square, Trash2, Send } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";

/**
 * Inline chat voice recorder.
 * Records up to maxSec seconds of audio/webm, shows a live timer,
 * uploads to /api/prompts/voice-upload, and calls onSend({voice_url, voice_duration}).
 *
 * Props:
 *   onSend({voice_url, voice_duration}) — called after successful upload
 *   maxSec (default 60)
 */
export default function ChatVoiceRecorder({ onSend, maxSec = 60 }) {
  const [recording, setRecording] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const recRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const startTsRef = useRef(0);
  const stoppedManuallyRef = useRef(false);

  useEffect(() => () => {
    // cleanup on unmount
    if (timerRef.current) clearInterval(timerRef.current);
    try { recRef.current?.stop(); } catch { /* ignore */ }
  }, []);

  const stopTracks = () => {
    try { recRef.current?.stream?.getTracks?.().forEach((t) => t.stop()); } catch { /* ignore */ }
  };

  const start = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      toast.error("Mikrofon qo'llab-quvvatlanmaydi");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
      const rec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      chunksRef.current = [];
      stoppedManuallyRef.current = false;
      rec.ondataavailable = (e) => { if (e.data?.size > 0) chunksRef.current.push(e.data); };
      rec.onstop = async () => {
        clearInterval(timerRef.current);
        const dur = Math.max(1, Math.round((Date.now() - startTsRef.current) / 1000));
        const blob = new Blob(chunksRef.current, { type: mime || "audio/webm" });
        stopTracks();
        setRecording(false);
        if (!stoppedManuallyRef.current) {
          // canceled — discard
          setSeconds(0);
          return;
        }
        if (dur < 1 || blob.size < 200) {
          toast.error("Juda qisqa yozildi");
          setSeconds(0);
          return;
        }
        setUploading(true);
        try {
          const fd = new FormData();
          fd.append("file", blob, "voice.webm");
          const r = await api.post("/prompts/voice-upload", fd, {
            headers: { "Content-Type": "multipart/form-data" },
          });
          const url = `${process.env.REACT_APP_BACKEND_URL}${r.data.url}`;
          await onSend?.({ voice_url: url, voice_duration: dur });
          setSeconds(0);
        } catch (e) {
          toast.error("Ovoz yuklab bo'lmadi");
        } finally {
          setUploading(false);
        }
      };
      rec.start();
      recRef.current = rec;
      startTsRef.current = Date.now();
      setRecording(true);
      setSeconds(0);
      timerRef.current = setInterval(() => {
        const s = Math.round((Date.now() - startTsRef.current) / 1000);
        setSeconds(s);
        if (s >= maxSec) {
          stoppedManuallyRef.current = true;
          try { rec.stop(); } catch { /* ignore */ }
        }
      }, 250);
    } catch (e) {
      toast.error("Mikrofon ruxsati kerak");
    }
  };

  const sendNow = () => {
    if (recording) {
      stoppedManuallyRef.current = true;
      try { recRef.current?.stop(); } catch { /* ignore */ }
    }
  };

  const cancel = () => {
    stoppedManuallyRef.current = false;
    try { recRef.current?.stop(); } catch { /* ignore */ }
    stopTracks();
    clearInterval(timerRef.current);
    setRecording(false);
    setSeconds(0);
    chunksRef.current = [];
  };

  if (uploading) {
    return (
      <button disabled className="p-2.5 rounded-full bg-primary/30 text-white inline-flex items-center gap-1.5 text-xs px-3" data-testid="voice-uploading">
        <span className="animate-pulse">⬆️</span> Yuklanmoqda...
      </button>
    );
  }

  if (recording) {
    return (
      <div className="flex items-center gap-1.5" data-testid="voice-recording">
        <button
          onClick={cancel}
          data-testid="voice-cancel"
          className="p-2 rounded-full bg-muted hover:bg-border"
          title="Bekor qilish"
        >
          <Trash2 className="w-4 h-4 text-rose-600" />
        </button>
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-500/15 border border-red-500/30">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <span className="text-xs font-mono tabular-nums">{seconds}s / {maxSec}s</span>
        </div>
        <button
          onClick={sendNow}
          data-testid="voice-send"
          className="p-2.5 rounded-full bg-primary text-white"
          title="Yuborish"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={start}
      data-testid="voice-start"
      className="w-10 h-10 grid place-items-center rounded-full bg-muted hover:bg-border"
      title="🎤"
    >
      <Mic className="w-4 h-4" />
    </button>
  );
}
