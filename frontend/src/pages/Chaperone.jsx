import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { toast } from "sonner";
import { Users, Copy, Trash2, Eye, UserPlus } from "lucide-react";
import { photoSrc } from "@/lib/photo";

export default function Chaperone() {
  const [tab, setTab] = useState("mine");
  const [mine, setMine] = useState([]);
  const [wards, setWards] = useState([]);
  const [invite, setInvite] = useState(null);
  const [acceptCode, setAcceptCode] = useState("");
  const [relation, setRelation] = useState("parent");

  const load = async () => {
    try {
      const m = await api.get("/chaperone/mine");
      setMine(m.data || []);
    } catch {}
    try {
      const w = await api.get("/chaperone/wards");
      setWards(w.data || []);
    } catch {}
  };
  useEffect(() => { load(); }, []);

  const createInvite = async () => {
    try {
      const r = await api.post("/chaperone/invite", { relation });
      setInvite(r.data);
      toast.success("Taklif kodi yaratildi");
    } catch (e) { toast.error("Xato"); }
  };

  const copy = (text) => {
    navigator.clipboard.writeText(text).then(() => toast.success("Nusxa olindi"));
  };

  const accept = async () => {
    if (!acceptCode.trim()) return;
    try {
      await api.post("/chaperone/accept", { code: acceptCode.trim().toUpperCase() });
      toast.success("Siz sovchi sifatida qabul qilindingiz");
      setAcceptCode("");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || "Xato"); }
  };

  const remove = async (id) => {
    if (!window.confirm("Aloqani uzasizmi?")) return;
    try {
      await api.delete(`/chaperone/${id}`);
      toast.success("Uzildi");
      load();
    } catch { toast.error("Xato"); }
  };

  return (
    <div className="p-5 max-w-3xl mx-auto pb-24" data-testid="chaperone-page">
      <div className="flex items-start gap-3 mb-5">
        <div className="w-12 h-12 rounded-2xl bg-secondary/10 text-secondary grid place-items-center">
          <Users className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-heading text-2xl font-semibold">Sovchi (Wali) tizimi</h1>
          <p className="text-sm text-muted-foreground">Ota-ona yoki yaqin qarindosh sizning chatlaringizni xolisona kuzata oladi — halol sovchilik uchun.</p>
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        <button data-testid="chap-tab-mine" onClick={() => setTab("mine")} className={`flex-1 rounded-2xl py-2.5 text-sm font-medium ${tab === "mine" ? "bg-primary text-white" : "bg-muted"}`}>
          Mening sovchilarim ({mine.length})
        </button>
        <button data-testid="chap-tab-wards" onClick={() => setTab("wards")} className={`flex-1 rounded-2xl py-2.5 text-sm font-medium ${tab === "wards" ? "bg-primary text-white" : "bg-muted"}`}>
          Men kuzatadiganlar ({wards.length})
        </button>
      </div>

      {tab === "mine" && (
        <>
          <div className="rounded-3xl bg-card border border-border p-4 mb-4">
            <h3 className="font-medium mb-3">Yangi sovchi taklif qilish</h3>
            <div className="flex gap-2 mb-3">
              {[["parent", "Ota-ona"], ["sibling", "Aka-uka/Opa-singil"], ["relative", "Qarindosh"], ["friend", "Do'st"]].map(([k, v]) => (
                <button key={k} onClick={() => setRelation(k)} className={`px-3 py-1.5 rounded-full text-xs border ${relation === k ? "bg-primary text-white border-primary" : "border-border"}`}>
                  {v}
                </button>
              ))}
            </div>
            <button data-testid="create-invite" onClick={createInvite} className="w-full rounded-2xl bg-secondary text-white py-3 font-medium inline-flex items-center justify-center gap-2">
              <UserPlus className="w-4 h-4" /> Taklif kodi yaratish
            </button>
            {invite && (
              <div className="mt-3 rounded-2xl bg-secondary/5 border border-secondary/30 p-3">
                <p className="text-xs text-muted-foreground">Taklif kodi</p>
                <div className="flex items-center gap-2 mt-1">
                  <code className="flex-1 font-mono text-lg font-semibold">{invite.code}</code>
                  <button onClick={() => copy(invite.code)} className="p-2 rounded-xl bg-card border border-border hover:bg-muted">
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
                {invite.link_tg && (
                  <a href={invite.link_tg} target="_blank" rel="noreferrer" className="mt-2 block text-xs text-secondary underline truncate">
                    Telegram link: {invite.link_tg}
                  </a>
                )}
                <p className="text-[11px] text-muted-foreground mt-2">Bu kodni sovchingizga ulashing — ular FIDEM ilovasida kodni kiritib qabul qiladi.</p>
              </div>
            )}
          </div>

          <div className="space-y-2">
            {mine.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-6">Hali sovchilar yo'q. Yuqoridagi tugma orqali taklif yarating.</p>
            ) : mine.map((m) => (
              <div key={m.id} className="rounded-2xl bg-card border border-border p-3 flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-muted overflow-hidden">
                  {m.wali.photo_url && <img src={photoSrc(m.wali.photo_url)} alt="" className="w-full h-full object-cover" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{m.wali.name}</p>
                  <p className="text-xs text-muted-foreground">{m.relation === "parent" ? "Ota-ona" : m.relation === "sibling" ? "Aka-opa" : m.relation}</p>
                </div>
                <button onClick={() => remove(m.id)} className="p-2 rounded-xl hover:bg-muted text-primary">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </>
      )}

      {tab === "wards" && (
        <>
          <div className="rounded-3xl bg-card border border-border p-4 mb-4">
            <h3 className="font-medium mb-2">Sovchi sifatida qabul qilish</h3>
            <p className="text-xs text-muted-foreground mb-3">Sizga ulashilgan taklif kodini kiriting</p>
            <div className="flex gap-2">
              <input
                data-testid="accept-code-input"
                value={acceptCode}
                onChange={(e) => setAcceptCode(e.target.value)}
                placeholder="KOD123"
                className="flex-1 rounded-2xl border border-border bg-card px-3 py-2.5 text-sm uppercase font-mono"
              />
              <button data-testid="accept-code-btn" onClick={accept} className="rounded-2xl bg-primary text-white px-5 py-2.5 text-sm font-medium">
                Qabul
              </button>
            </div>
          </div>

          <div className="space-y-2">
            {wards.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-6">Hali hech kimni kuzatmaysiz.</p>
            ) : wards.map((w) => (
              <div key={w.id} className="rounded-2xl bg-card border border-border p-3 flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-muted overflow-hidden">
                  {w.ward.photo_url && <img src={photoSrc(w.ward.photo_url)} alt="" className="w-full h-full object-cover" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{w.ward.name}</p>
                  <p className="text-xs text-muted-foreground">{w.relation === "parent" ? "Farzand" : w.relation}</p>
                </div>
                <Link to={`/chaperone/ward/${w.ward.id}`} className="p-2 rounded-xl hover:bg-muted text-secondary">
                  <Eye className="w-4 h-4" />
                </Link>
                <button onClick={() => remove(w.id)} className="p-2 rounded-xl hover:bg-muted text-primary">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
