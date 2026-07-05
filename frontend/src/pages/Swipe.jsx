import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { photoSrc } from "@/lib/photo";
import { toast } from "sonner";
import { X, Heart, RotateCcw, MessageCircle } from "lucide-react";

/**
 * Tinder-style swipe deck.
 * Window-level drag listeners + requestAnimationFrame + CSS will-change for 60fps.
 */
export default function Swipe() {
  const { t } = useApp();
  const nav = useNavigate();
  const [items, setItems] = useState([]);
  const [idx, setIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [history, setHistory] = useState([]);
  const [drag, setDrag] = useState({ x: 0, y: 0, dragging: false });
  const startRef = useRef({ x: 0, y: 0 });
  const dragRef = useRef({ x: 0, y: 0, dragging: false });
  const rafRef = useRef(0);
  const cardElRef = useRef(null);
  const movingRef = useRef(false);

  useEffect(() => {
    setLoading(true);
    api.get("/candidates", { params: { sort: "match", limit: 40 } })
      .then((r) => setItems(r.data || []))
      .catch(() => { /* ignore */ })
      .finally(() => setLoading(false));
  }, []);

  const current = items[idx];
  const next1 = items[idx + 1];

  const applyTransform = () => {
    const el = cardElRef.current;
    if (!el) return;
    const { x, y, dragging } = dragRef.current;
    if (dragging) {
      const rot = x / 12;
      el.style.transform = `translate3d(${x}px, ${y}px, 0) rotate(${rot}deg)`;
      el.style.transition = "none";
    } else {
      el.style.transform = "translate3d(0,0,0) rotate(0deg)";
      el.style.transition = "transform 0.25s ease-out";
    }
  };

  const scheduleApply = () => {
    if (rafRef.current) return;
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = 0;
      applyTransform();
      setDrag({ ...dragRef.current });
    });
  };

  const advance = (kind) => {
    setHistory((h) => [...h, { kind, candidate: current }]);
    setIdx((i) => i + 1);
    dragRef.current = { x: 0, y: 0, dragging: false };
    setDrag({ x: 0, y: 0, dragging: false });
    const el = cardElRef.current;
    if (el) { el.style.transform = "translate3d(0,0,0)"; el.style.transition = "none"; }
  };

  const handlePass = () => { if (current) advance("pass"); };
  const handleLike = async () => {
    if (!current) return;
    const target = current;
    advance("like");
    try {
      await api.post("/saved", { user_id: target.id });
      toast.success(`${target.name} saqlandi ❤️`);
    } catch (e) { /* ignore */ }
  };
  const handleSuper = async () => {
    if (!current) return;
    const target = current;
    advance("super");
    try {
      await api.post("/roses/send", { to_user_id: target.id, note: "Sizdan juda manfaatdorman!" });
      toast.success(`🌹 ${target.name} ga yuborildi`);
    } catch (e) {
      toast.error("Atirgul yuborib bo'lmadi");
    }
  };

  const undo = () => {
    if (history.length === 0 || idx === 0) return;
    setHistory((h) => h.slice(0, -1));
    setIdx((i) => Math.max(0, i - 1));
  };

  const onMove = (e) => {
    if (!movingRef.current) return;
    const p = e.touches?.[0] || e;
    const dx = p.clientX - startRef.current.x;
    const dy = p.clientY - startRef.current.y;
    dragRef.current.x = dx;
    dragRef.current.y = dy;
    scheduleApply();
  };

  const stopDrag = () => {
    movingRef.current = false;
    window.removeEventListener("mousemove", onMove);
    window.removeEventListener("mouseup", onUp);
    window.removeEventListener("touchmove", onMove);
    window.removeEventListener("touchend", onUp);
    window.removeEventListener("touchcancel", onUp);
  };

  const onUp = () => {
    if (!movingRef.current) return;
    const { x, y } = dragRef.current;
    const threshold = 110;
    stopDrag();
    if (x > threshold) handleLike();
    else if (x < -threshold) handlePass();
    else if (y < -threshold) handleSuper();
    else {
      dragRef.current = { x: 0, y: 0, dragging: false };
      setDrag({ x: 0, y: 0, dragging: false });
      const el = cardElRef.current;
      if (el) { el.style.transform = "translate3d(0,0,0) rotate(0deg)"; el.style.transition = "transform 0.25s ease-out"; }
    }
  };

  const onDown = (e) => {
    const p = e.touches?.[0] || e;
    startRef.current = { x: p.clientX, y: p.clientY };
    dragRef.current = { x: 0, y: 0, dragging: true };
    movingRef.current = true;
    setDrag({ x: 0, y: 0, dragging: true });
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    window.addEventListener("touchmove", onMove, { passive: true });
    window.addEventListener("touchend", onUp);
    window.addEventListener("touchcancel", onUp);
  };

  useEffect(() => () => stopDrag(), [stopDrag]);

  if (loading) {
    return (
      <div className="min-h-[70vh] grid place-items-center">
        <div className="w-10 h-10 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
      </div>
    );
  }

  if (!current) {
    return (
      <div className="px-5 pt-8 text-center space-y-4">
        <div className="text-6xl">🎉</div>
        <h2 className="text-xl font-heading font-semibold">Hozircha hammasi shu</h2>
        <p className="text-sm text-muted-foreground">Yangi nomzodlar tez kunda paydo bo'ladi. Filtrlaringizni kengaytirib ko'ring.</p>
        <button onClick={() => nav("/")} data-testid="swipe-go-list" className="inline-flex px-5 py-3 rounded-2xl bg-primary text-white font-medium">
          Ro'yxatga qaytish
        </button>
      </div>
    );
  }

  const likeOpacity = Math.min(1, Math.max(0, drag.x / 100));
  const passOpacity = Math.min(1, Math.max(0, -drag.x / 100));
  const superOpacity = Math.min(1, Math.max(0, -drag.y / 100));
  const remaining = items.length - idx;

  return (
    <div className="px-3 pt-3 pb-4 select-none">
      <div className="flex items-center justify-between px-2 pb-3">
        <h1 className="font-heading text-xl font-semibold">Swipe</h1>
        <button onClick={() => nav("/")} data-testid="swipe-exit" className="text-xs px-3 py-1.5 rounded-full bg-muted">Ro'yxat ko'rinishi</button>
      </div>

      <div className="relative" style={{ height: "calc(100vh - 280px)", minHeight: 460 }}>
        {next1 && (
          <div className="absolute inset-0 rounded-3xl overflow-hidden shadow-md scale-[0.96] opacity-70 pointer-events-none">
            <CardImage c={next1} />
          </div>
        )}

        <div
          ref={cardElRef}
          data-testid="swipe-card"
          className="absolute inset-0 rounded-3xl overflow-hidden shadow-xl bg-card cursor-grab active:cursor-grabbing"
          style={{ touchAction: "none", willChange: "transform" }}
          onMouseDown={onDown}
          onTouchStart={onDown}
        >
          <CardImage c={current} />
          <div className="absolute top-6 left-6 px-4 py-1.5 rounded-xl border-4 border-emerald-500 text-emerald-500 font-bold rotate-[-15deg] text-2xl bg-white/80" style={{ opacity: likeOpacity }}>LIKE</div>
          <div className="absolute top-6 right-6 px-4 py-1.5 rounded-xl border-4 border-rose-500 text-rose-500 font-bold rotate-[15deg] text-2xl bg-white/80" style={{ opacity: passOpacity }}>NOPE</div>
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 px-4 py-1.5 rounded-xl border-4 border-yellow-500 text-yellow-600 font-bold text-2xl bg-white/80" style={{ opacity: superOpacity }}>🌹 ATIRGUL</div>
        </div>
      </div>

      <div className="flex items-center justify-center gap-3 pt-5">
        <button data-testid="swipe-undo" onClick={undo} disabled={idx === 0} className="w-12 h-12 rounded-full border-2 border-border bg-card grid place-items-center disabled:opacity-40 hover:scale-105 transition shadow"><RotateCcw className="w-5 h-5 text-yellow-600" /></button>
        <button data-testid="swipe-pass" onClick={handlePass} className="w-16 h-16 rounded-full border-2 border-rose-500/30 bg-white grid place-items-center hover:scale-105 transition shadow-lg"><X className="w-7 h-7 text-rose-500" strokeWidth={3} /></button>
        <button data-testid="swipe-super" onClick={handleSuper} className="w-14 h-14 rounded-full bg-gradient-to-br from-yellow-400 to-amber-500 text-white grid place-items-center hover:scale-105 transition shadow-lg"><span className="text-2xl">🌹</span></button>
        <button data-testid="swipe-like" onClick={handleLike} className="w-16 h-16 rounded-full border-2 border-emerald-500/30 bg-white grid place-items-center hover:scale-105 transition shadow-lg"><Heart className="w-7 h-7 text-emerald-500 fill-emerald-500" /></button>
        <button data-testid="swipe-chat" onClick={() => nav(`/chat/${current.id}`)} className="w-12 h-12 rounded-full border-2 border-border bg-card grid place-items-center hover:scale-105 transition shadow"><MessageCircle className="w-5 h-5 text-foreground" /></button>
      </div>

      <p className="text-center text-[11px] text-muted-foreground pt-3">{remaining} ta qoldi · Swipe yoki tugma bosing</p>
    </div>
  );
}

function CardImage({ c }) {
  const url = photoSrc(c.photo_url);
  return (
    <div className="relative w-full h-full bg-muted">
      <img
        src={url}
        alt={c.name}
        loading="lazy"
        decoding="async"
        draggable="false"
        className={`absolute inset-0 w-full h-full object-cover pointer-events-none ${c.photo_unlocked ? "" : "blur-photo"}`}
      />
      <div className="absolute top-3 left-3 right-3 flex items-start justify-between pointer-events-none">
        <span className={`px-2.5 py-1 rounded-full text-[11px] font-medium ${c.match_score >= 80 ? "bg-emerald-600 text-white" : c.match_score >= 60 ? "bg-primary text-white" : "bg-yellow-500 text-white"}`}>
          {c.match_score}%
        </span>
        <div className="flex gap-1">
          {c.verified_selfie && <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 text-[10px]">✓ Verified</span>}
          {c.verified_financial && <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 text-[10px]">💎</span>}
          {c.boosted && <span className="px-2 py-0.5 rounded-full bg-primary/20 text-foreground text-[10px]">🚀 Boost</span>}
        </div>
      </div>
      <div className="absolute bottom-0 inset-x-0 p-4 bg-gradient-to-t from-black/85 via-black/50 to-transparent text-white pointer-events-none">
        <h3 className="text-2xl font-heading font-bold">{c.name}, {c.age}</h3>
        <p className="text-sm opacity-90">{c.region} · {c.profession || "—"}</p>
        {c.match_reasons?.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {c.match_reasons.slice(0, 3).map((r, i) => (
              <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-white/20 backdrop-blur">{r}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
