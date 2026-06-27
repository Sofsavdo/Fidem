import React, { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { photoSrc } from "@/lib/photo";
import { toast } from "sonner";
import { X, Heart, Star, Bookmark, RotateCcw, MessageCircle } from "lucide-react";

/**
 * Tinder-style swipe deck.
 * Loads candidates via /api/candidates and lets user swipe left (pass) or right (like = save).
 * Up = super-application via Roses.
 * Includes undo (last action) and exit-to-list button.
 */
export default function Swipe() {
  const { t } = useApp();
  const nav = useNavigate();
  const [items, setItems] = useState([]);
  const [idx, setIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [history, setHistory] = useState([]); // {kind, candidate}
  const [drag, setDrag] = useState({ x: 0, y: 0, dragging: false });
  const startRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    setLoading(true);
    api.get("/candidates", { params: { sort: "match", limit: 40 } })
      .then((r) => setItems(r.data || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const current = items[idx];
  const next1 = items[idx + 1];

  const onPointerDown = (e) => {
    const p = e.touches?.[0] || e;
    startRef.current = { x: p.clientX, y: p.clientY };
    setDrag({ x: 0, y: 0, dragging: true });
  };
  const onPointerMove = (e) => {
    if (!drag.dragging) return;
    const p = e.touches?.[0] || e;
    const dx = p.clientX - startRef.current.x;
    const dy = p.clientY - startRef.current.y;
    setDrag({ x: dx, y: dy, dragging: true });
  };
  const onPointerUp = () => {
    if (!drag.dragging) return;
    const threshold = 110;
    if (drag.x > threshold) handleLike();
    else if (drag.x < -threshold) handlePass();
    else if (drag.y < -threshold) handleSuper();
    else setDrag({ x: 0, y: 0, dragging: false });
  };

  const advance = (kind) => {
    setHistory((h) => [...h, { kind, candidate: current }]);
    setDrag({ x: 0, y: 0, dragging: false });
    setIdx((i) => i + 1);
  };

  const handlePass = () => {
    if (!current) return;
    advance("pass");
  };
  const handleLike = async () => {
    if (!current) return;
    try {
      await api.post("/saved", { user_id: current.id });
      toast.success(`${current.name} saqlandi ❤️`);
    } catch (e) {
      // Already saved or other — ignore but proceed
    }
    advance("like");
  };
  const handleSuper = async () => {
    if (!current) return;
    try {
      const r = await api.post("/roses/send", { to_user_id: current.id, note: "Sizdan juda manfaatdorman!" });
      toast.success(`🌹 ${current.name} ga yuborildi`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Atirgul yuborib bo'lmadi");
    }
    advance("super");
  };

  const undo = () => {
    if (history.length === 0 || idx === 0) return;
    setHistory((h) => h.slice(0, -1));
    setIdx((i) => Math.max(0, i - 1));
    setDrag({ x: 0, y: 0, dragging: false });
  };

  const remaining = items.length - idx;
  const rotation = useMemo(() => (drag.x / 12).toFixed(2), [drag.x]);
  const cardStyle = drag.dragging
    ? { transform: `translate(${drag.x}px, ${drag.y}px) rotate(${rotation}deg)`, transition: "none" }
    : { transform: "translate(0,0) rotate(0deg)" };

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

  return (
    <div className="px-3 pt-3 pb-4 select-none">
      <div className="flex items-center justify-between px-2 pb-3">
        <h1 className="font-heading text-xl font-semibold">Swipe</h1>
        <button onClick={() => nav("/")} data-testid="swipe-exit" className="text-xs px-3 py-1.5 rounded-full bg-muted">Ro'yxat ko'rinishi</button>
      </div>

      <div className="relative" style={{ height: "calc(100vh - 280px)", minHeight: 460 }}>
        {/* Next card peeking */}
        {next1 && (
          <div className="absolute inset-0 rounded-3xl overflow-hidden shadow-md scale-[0.96] opacity-70 pointer-events-none">
            <CardImage c={next1} />
          </div>
        )}

        {/* Current card */}
        <div
          data-testid="swipe-card"
          className="absolute inset-0 rounded-3xl overflow-hidden shadow-xl bg-card cursor-grab active:cursor-grabbing"
          style={cardStyle}
          onMouseDown={onPointerDown}
          onMouseMove={onPointerMove}
          onMouseUp={onPointerUp}
          onMouseLeave={onPointerUp}
          onTouchStart={onPointerDown}
          onTouchMove={onPointerMove}
          onTouchEnd={onPointerUp}
        >
          <CardImage c={current} />

          {/* Swipe action badges */}
          <div
            className="absolute top-6 left-6 px-4 py-1.5 rounded-xl border-4 border-emerald-500 text-emerald-500 font-bold rotate-[-15deg] text-2xl bg-white/80"
            style={{ opacity: likeOpacity }}
          >
            LIKE
          </div>
          <div
            className="absolute top-6 right-6 px-4 py-1.5 rounded-xl border-4 border-rose-500 text-rose-500 font-bold rotate-[15deg] text-2xl bg-white/80"
            style={{ opacity: passOpacity }}
          >
            NOPE
          </div>
          <div
            className="absolute top-1/3 left-1/2 -translate-x-1/2 px-4 py-1.5 rounded-xl border-4 border-yellow-500 text-yellow-600 font-bold text-2xl bg-white/80"
            style={{ opacity: superOpacity }}
          >
            🌹 ATIRGUL
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-center gap-3 pt-5">
        <button
          data-testid="swipe-undo"
          onClick={undo}
          disabled={idx === 0}
          className="w-12 h-12 rounded-full border-2 border-border bg-card grid place-items-center disabled:opacity-40 hover:scale-105 transition shadow"
          title="Orqaga"
        >
          <RotateCcw className="w-5 h-5 text-yellow-600" />
        </button>
        <button
          data-testid="swipe-pass"
          onClick={handlePass}
          className="w-16 h-16 rounded-full border-2 border-rose-500/30 bg-white grid place-items-center hover:scale-105 transition shadow-lg"
          title="O'tkazib yuborish"
        >
          <X className="w-7 h-7 text-rose-500" strokeWidth={3} />
        </button>
        <button
          data-testid="swipe-super"
          onClick={handleSuper}
          className="w-14 h-14 rounded-full bg-gradient-to-br from-yellow-400 to-amber-500 text-white grid place-items-center hover:scale-105 transition shadow-lg"
          title="🌹 Atirgul yuborish"
        >
          <span className="text-2xl">🌹</span>
        </button>
        <button
          data-testid="swipe-like"
          onClick={handleLike}
          className="w-16 h-16 rounded-full border-2 border-emerald-500/30 bg-white grid place-items-center hover:scale-105 transition shadow-lg"
          title="Yoqdi"
        >
          <Heart className="w-7 h-7 text-emerald-500 fill-emerald-500" />
        </button>
        <button
          data-testid="swipe-chat"
          onClick={() => nav(`/chat/${current.id}`)}
          className="w-12 h-12 rounded-full border-2 border-border bg-card grid place-items-center hover:scale-105 transition shadow"
          title="Yozish"
        >
          <MessageCircle className="w-5 h-5 text-primary" />
        </button>
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
        className={`absolute inset-0 w-full h-full object-cover ${c.photo_unlocked ? "" : "blur-photo"}`}
      />
      {/* Top: badges */}
      <div className="absolute top-3 left-3 right-3 flex items-start justify-between">
        <span className={`px-2.5 py-1 rounded-full text-[11px] font-medium ${c.match_score >= 80 ? "bg-emerald-600 text-white" : c.match_score >= 60 ? "bg-primary text-white" : "bg-yellow-500 text-white"}`}>
          {c.match_score}%
        </span>
        <div className="flex gap-1">
          {c.verified_selfie && <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 text-[10px]">✓ Verified</span>}
          {c.verified_financial && <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 text-[10px]">💎</span>}
          {c.boosted && <span className="px-2 py-0.5 rounded-full bg-primary/20 text-primary text-[10px]">🚀 Boost</span>}
        </div>
      </div>
      {/* Bottom: info */}
      <div className="absolute bottom-0 inset-x-0 p-4 bg-gradient-to-t from-black/85 via-black/50 to-transparent text-white">
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
