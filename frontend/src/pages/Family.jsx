import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import { Phone, Users, Send, CheckCircle2, XCircle, Clock, Crown, Save } from "lucide-react";
import { photoSrc } from "@/lib/photo";

export default function Family() {
  const { user } = useApp();
  const [contact, setContact] = useState(null);
  const [requests, setRequests] = useState({ sent: [], received: [] });
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [relation, setRelation] = useState("parent");
  const [savingContact, setSavingContact] = useState(false);

  const load = async () => {
    try {
      const [c, r] = await Promise.all([api.get("/family/contacts/mine"), api.get("/family/mine")]);
      setContact(c.data.family_contact || null);
      setRequests(r.data || { sent: [], received: [] });
      if (c.data.family_contact) {
        setPhone(c.data.family_contact.phone || "");
        setName(c.data.family_contact.name || "");
        setRelation(c.data.family_contact.relation || "parent");
      }
    } catch (e) { /* ignore */ }
  };

  useEffect(() => { load(); }, []);

  const saveContact = async () => {
    if (phone.replace(/\D/g, "").length < 9) {
      toast.error("Telefon raqamini to'liq kiriting");
      return;
    }
    setSavingContact(true);
    try {
      await api.patch("/family/contacts", { parent_phone: phone, parent_name: name, parent_relation: relation });
      toast.success("Oilaviy aloqa saqlandi");
      load();
    } catch (e) {
      toast.error("Xato");
    } finally { setSavingContact(false); }
  };

  const respond = async (id, accept) => {
    try {
      await api.post(`/family/respond/${id}`, { accept });
      toast.success(accept ? "Qabul qilindi — telefonlar ko'rinishga tayyor!" : "Rad etildi");
      load();
    } catch (e) {
      toast.error("Xato");
    }
  };

  const statusBadge = (s) => {
    const map = {
      pending: { cls: "bg-amber-100 text-amber-700", icon: <Clock className="w-3 h-3" />, label: "Kutilmoqda" },
      accepted: { cls: "bg-emerald-100 text-emerald-700", icon: <CheckCircle2 className="w-3 h-3" />, label: "Qabul qilindi" },
      rejected: { cls: "bg-rose-100 text-rose-700", icon: <XCircle className="w-3 h-3" />, label: "Rad etildi" },
    };
    const m = map[s] || { cls: "bg-muted text-muted-foreground", icon: null, label: s };
    return <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full ${m.cls}`}>{m.icon}{m.label}</span>;
  };

  const isVip = user?.plan === "vip";

  return (
    <div className="max-w-3xl mx-auto p-4 md:p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-heading font-semibold flex items-center gap-2">
          <Users className="w-6 h-6 text-primary" /> Oilaviy aloqa
        </h1>
        <p className="text-sm text-muted-foreground mt-1">VIP foydalanuvchilar uchun — jiddiy bosqichda ota-ona telefon raqamlarini xavfsiz almashish.</p>
      </div>

      {!isVip && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 flex gap-3">
          <Crown className="w-5 h-5 text-amber-600 shrink-0" />
          <div className="text-sm">
            <p className="font-medium text-amber-900">VIP tarif talab qilinadi</p>
            <p className="text-amber-800 mt-1">Oilaviy aloqa funksiyasi faqat VIP foydalanuvchilar uchun. <a href="/premium" className="underline font-medium">VIP olish</a></p>
          </div>
        </div>
      )}

      {/* Set family contact */}
      <div className="rounded-3xl border border-border bg-card p-5 space-y-3">
        <h2 className="font-semibold flex items-center gap-2"><Phone className="w-4 h-4" /> Oilaviy telefonimni kiritish</h2>
        <p className="text-xs text-muted-foreground">Bu raqam faqat siz qabul qilgan/yuborgan oilaviy aloqa so'rovlarida ikkinchi tomonga ko'rinadi.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <input data-testid="fam-phone" placeholder="+998 90 123 45 67" className="px-4 py-2.5 rounded-xl border border-input bg-background text-sm" value={phone} onChange={(e) => setPhone(e.target.value)} />
          <input data-testid="fam-name" placeholder="Ism (otam Karim aka)" className="px-4 py-2.5 rounded-xl border border-input bg-background text-sm" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <select data-testid="fam-relation" className="w-full px-4 py-2.5 rounded-xl border border-input bg-background text-sm" value={relation} onChange={(e) => setRelation(e.target.value)}>
          <option value="parent">Ota / Ona</option>
          <option value="sibling">Aka / Opa</option>
          <option value="relative">Qarindosh</option>
          <option value="guardian">Vasiy</option>
        </select>
        <button data-testid="fam-save" onClick={saveContact} disabled={savingContact} className="w-full py-2.5 rounded-xl bg-primary text-white font-medium text-sm disabled:opacity-50 inline-flex items-center justify-center gap-2">
          <Save className="w-4 h-4" /> Saqlash
        </button>
      </div>

      {/* Received requests */}
      <div className="rounded-3xl border border-border bg-card p-5">
        <h2 className="font-semibold mb-3">Kelgan so'rovlar ({requests.received.length})</h2>
        {requests.received.length === 0 ? (
          <p className="text-sm text-muted-foreground">Hozircha so'rov yo'q</p>
        ) : (
          <div className="space-y-3">
            {requests.received.map((r) => (
              <div key={r.id} className="flex items-center gap-3 p-3 rounded-xl bg-muted/40">
                <div className="w-10 h-10 rounded-full bg-muted overflow-hidden">
                  {r.peer?.photo_url && <img loading="lazy" decoding="async" src={photoSrc(r.peer.photo_url)} alt="" className="w-full h-full object-cover" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{r.peer?.name}</p>
                  {r.note && <p className="text-xs text-muted-foreground line-clamp-2">{r.note}</p>}
                </div>
                {r.status === "pending" ? (
                  <div className="flex gap-2">
                    <button onClick={() => respond(r.id, true)} className="px-3 py-1.5 rounded-lg bg-primary text-white text-xs">Qabul</button>
                    <button onClick={() => respond(r.id, false)} className="px-3 py-1.5 rounded-lg border border-input text-xs">Rad et</button>
                  </div>
                ) : statusBadge(r.status)}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Sent requests */}
      <div className="rounded-3xl border border-border bg-card p-5">
        <h2 className="font-semibold mb-3">Yuborilgan so'rovlar ({requests.sent.length})</h2>
        {requests.sent.length === 0 ? (
          <p className="text-sm text-muted-foreground">Hozircha yuborilmagan</p>
        ) : (
          <div className="space-y-2">
            {requests.sent.map((r) => (
              <FamilyRow key={r.id} request={r} statusBadge={statusBadge} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function FamilyRow({ request, statusBadge }) {
  const [contact, setContact] = useState(null);
  const [show, setShow] = useState(false);
  const fetchContact = async () => {
    try {
      const r = await api.get(`/family/contact/${request.peer?.id}`);
      setContact(r.data);
      setShow(true);
    } catch (e) { toast.error("Xato"); }
  };
  return (
    <div className="p-3 rounded-xl bg-muted/40">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-muted overflow-hidden">
          {request.peer?.photo_url && <img loading="lazy" decoding="async" src={photoSrc(request.peer.photo_url)} alt="" className="w-full h-full object-cover" />}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium">{request.peer?.name}</p>
          <p className="text-[11px] text-muted-foreground">{new Date(request.created_at).toLocaleString("uz-UZ")}</p>
        </div>
        {statusBadge(request.status)}
      </div>
      {request.status === "accepted" && !show && (
        <button onClick={fetchContact} className="mt-2 text-xs text-primary underline">Ularning oilaviy telefonini ko'rsatish</button>
      )}
      {show && contact && (
        <div className="mt-2 p-3 rounded-lg bg-card border border-border text-sm">
          <p className="font-medium">{contact.family_contact.name || "Oilaviy aloqa"}</p>
          <p className="text-muted-foreground capitalize text-xs">{contact.family_contact.relation}</p>
          <a href={`tel:${contact.family_contact.phone}`} className="mt-1 inline-flex items-center gap-1 text-primary font-medium">
            <Phone className="w-4 h-4" /> {contact.family_contact.phone}
          </a>
        </div>
      )}
    </div>
  );
}
