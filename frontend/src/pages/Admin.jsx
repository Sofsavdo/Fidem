import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import { Link } from "react-router-dom";
import { ArrowLeft, ShieldCheck, Wallet, Users as UsersIcon, DollarSign } from "lucide-react";
import { photoSrc } from "@/lib/photo";

export default function Admin() {
  const { user, t } = useApp();
  const [stats, setStats] = useState(null);
  const [tab, setTab] = useState("dashboard");

  useEffect(() => {
    api.get("/admin/stats").then((r) => setStats(r.data)).catch(() => {});
  }, []);

  if (!user) return null;
  if (!user.is_admin) {
    return <div className="p-8 text-center text-muted-foreground" data-testid="admin-no-access">Faqat admin uchun</div>;
  }

  return (
    <div className="px-4 pt-6 pb-8 space-y-5">
      <div className="flex items-center gap-3">
        <Link to="/me" className="p-2 rounded-full hover:bg-muted" data-testid="admin-back">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="font-heading text-3xl font-semibold tracking-tight">{t("admin_panel")}</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 overflow-x-auto no-scrollbar">
        {[
          ["dashboard", "Dashboard"],
          ["users", t("users")],
          ["payments", t("payments")],
          ["verifications", t("verifications")],
          ["withdrawals", "Yechishlar"],
          ["concierge", "Concierge"],
          ["reports", t("reports")],
        ].map(([k, l]) => (
          <button
            key={k}
            data-testid={`admin-tab-${k}`}
            onClick={() => setTab(k)}
            className={`whitespace-nowrap rounded-full px-3 py-1.5 text-xs border ${
              tab === k ? "bg-foreground text-background border-foreground" : "bg-card border-border"
            }`}
          >
            {l}
          </button>
        ))}
      </div>

      {tab === "dashboard" && stats && (
        <div className="grid grid-cols-2 gap-3 stagger" data-testid="admin-stats">
          <StatCard label={t("users")} value={stats.total_users} icon={<UsersIcon className="w-4 h-4" />} />
          <StatCard label={t("dau")} value={stats.dau} />
          <StatCard label={t("wau")} value={stats.wau} />
          <StatCard label={t("conversion")} value={`${stats.conversion_premium}%`} />
          <StatCard label="Premium" value={stats.premium} />
          <StatCard label="VIP" value={stats.vip} />
          <StatCard label={t("male_female_ratio")} value={`${stats.males} / ${stats.females}`} />
          <StatCard label={t("revenue")} value={`${(stats.revenue_uzs || 0).toLocaleString()} so'm`} icon={<DollarSign className="w-4 h-4" />} />
          <StatCard label="Pending pay" value={stats.pending_payments} />
          <StatCard label="Pending verif" value={stats.pending_verifications} />
        </div>
      )}

      {tab === "users" && <AdminUsers />}
      {tab === "payments" && <AdminPayments />}
      {tab === "verifications" && <AdminVerifications />}
      {tab === "withdrawals" && <AdminWithdrawals />}
      {tab === "concierge" && <AdminConcierge />}
      {tab === "reports" && <AdminReports />}
    </div>
  );
}

const StatCard = React.memo(function StatCard({ label, value, icon }) {
  return (
    <div className="rounded-3xl bg-card border border-border p-4">
      <div className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1">{icon}{label}</div>
      <p className="font-heading text-2xl mt-1">{value}</p>
    </div>
  );
});

function AdminUsers() {
  const [q, setQ] = useState("");
  const [list, setList] = useState([]);
  const load = () => api.get("/admin/users", { params: { q } }).then((r) => setList(r.data || []));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [q]);
  const patch = async (id, patch) => {
    await api.patch(`/admin/users/${id}`, patch);
    load();
    toast.success("Updated");
  };
  return (
    <div className="space-y-2" data-testid="admin-users">
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search..." className="w-full rounded-2xl border border-border bg-card px-4 py-3" data-testid="admin-user-search" />
      {list.map((u) => (
        <div key={u.id} className="rounded-2xl bg-card border border-border p-3" data-testid={`admin-user-${u.id}`}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-muted overflow-hidden">
              {u.photo_url && <img loading="lazy" decoding="async" src={photoSrc(u.photo_url)} alt="" className="w-full h-full object-cover" />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{u.name} · {u.plan} {u.blocked ? "🚫" : ""}</p>
              <p className="text-xs text-muted-foreground truncate">{u.region} · age {u.age} · {u.gender}</p>
            </div>
          </div>
          <div className="flex gap-1 mt-2 flex-wrap">
            <button data-testid={`adm-verify-selfie-${u.id}`} onClick={() => patch(u.id, { verified_selfie: !u.verified_selfie })} className="text-[10px] rounded-full bg-secondary/10 text-secondary px-2 py-1">{u.verified_selfie ? "✓ Selfie" : "Verify selfie"}</button>
            <button data-testid={`adm-verify-fin-${u.id}`} onClick={() => patch(u.id, { verified_financial: !u.verified_financial })} className="text-[10px] rounded-full bg-gold-light text-yellow-900 px-2 py-1">{u.verified_financial ? "💎 Financial" : "Verify financial"}</button>
            <button data-testid={`adm-premium-${u.id}`} onClick={() => patch(u.id, { plan: u.plan === "premium" ? "free" : "premium" })} className="text-[10px] rounded-full bg-primary/10 text-foreground px-2 py-1">{u.plan === "premium" ? "Cancel Premium" : "Make Premium"}</button>
            <button data-testid={`adm-vip-${u.id}`} onClick={() => patch(u.id, { plan: u.plan === "vip" ? "free" : "vip" })} className="text-[10px] rounded-full bg-ink text-gold px-2 py-1">{u.plan === "vip" ? "Cancel VIP" : "Make VIP"}</button>
            <button data-testid={`adm-add-${u.id}`} onClick={() => patch(u.id, { add_balance: 10000 })} className="text-[10px] rounded-full border border-border px-2 py-1">+10k</button>
            <button data-testid={`adm-block-${u.id}`} onClick={() => patch(u.id, { blocked: !u.blocked })} className="text-[10px] rounded-full bg-red-50 text-red-700 px-2 py-1">{u.blocked ? "Unblock" : "Block"}</button>
          </div>
        </div>
      ))}
    </div>
  );
}

function AdminPayments() {
  const [list, setList] = useState([]);
  const load = () => api.get("/admin/payments").then((r) => setList(r.data || []));
  useEffect(() => { load(); }, []);
  const confirm = async (id) => {
    await api.post(`/payments/admin-confirm/${id}`);
    toast.success("Confirmed");
    load();
  };
  return (
    <div className="space-y-2" data-testid="admin-payments">
      {list.map((p) => (
        <div key={p.id} className="rounded-2xl bg-card border border-border p-3 flex items-center justify-between" data-testid={`adm-pay-${p.id}`}>
          <div>
            <p className="text-sm">{p.purpose} · {p.amount?.toLocaleString()} so'm</p>
            <p className="text-xs text-muted-foreground">{p.status}</p>
          </div>
          {p.status !== "success" && (
            <button data-testid={`adm-pay-confirm-${p.id}`} onClick={() => confirm(p.id)} className="text-xs rounded-full bg-secondary text-white px-3 py-1.5">Confirm</button>
          )}
        </div>
      ))}
    </div>
  );
}

function AdminVerifications() {
  const [list, setList] = useState([]);
  const load = () => api.get("/admin/verifications").then((r) => setList(r.data || []));
  useEffect(() => { load(); }, []);
  const decide = async (id, approve) => {
    await api.post(`/admin/verifications/${id}/decide`, { approve });
    load();
  };
  return (
    <div className="space-y-2" data-testid="admin-verifs">
      {list.length === 0 && <p className="text-sm text-muted-foreground">No pending</p>}
      {list.map((v) => (
        <div key={v.id} className="rounded-2xl bg-card border border-border p-3 flex items-center justify-between" data-testid={`adm-verif-${v.id}`}>
          <div>
            <p className="text-sm">{v.kind} — {v.user_id?.slice(0, 8)}</p>
            <p className="text-xs text-muted-foreground">{v.note}</p>
          </div>
          <div className="flex gap-1">
            <button data-testid={`adm-verif-yes-${v.id}`} onClick={() => decide(v.id, true)} className="text-xs rounded-full bg-secondary text-white px-3 py-1.5">✓</button>
            <button data-testid={`adm-verif-no-${v.id}`} onClick={() => decide(v.id, false)} className="text-xs rounded-full border border-border px-3 py-1.5">✕</button>
          </div>
        </div>
      ))}
    </div>
  );
}

function AdminReports() {
  const [list, setList] = useState([]);
  useEffect(() => { api.get("/admin/reports").then((r) => setList(r.data || [])); }, []);
  return (
    <div className="space-y-2" data-testid="admin-reports">
      {list.length === 0 && <p className="text-sm text-muted-foreground">No reports</p>}
      {list.map((r) => (
        <div key={r.id} className="rounded-2xl bg-card border border-border p-3">
          <p className="text-sm">{r.reason}</p>
          <p className="text-xs text-muted-foreground">From {r.reporter_id?.slice(0, 8)} → {r.target_id?.slice(0, 8)}</p>
        </div>
      ))}
    </div>
  );
}

function AdminWithdrawals() {
  const [list, setList] = useState([]);
  const [filter, setFilter] = useState("pending");
  const load = () => api.get("/admin/withdrawals", { params: { status: filter || undefined } }).then((r) => setList(r.data || []));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filter]);
  const approve = async (id) => { await api.post(`/admin/withdrawals/${id}/approve`); toast.success("Tasdiqlandi"); load(); };
  const reject = async (id) => {
    const reason = prompt("Rad etish sababi:") || "";
    await api.post(`/admin/withdrawals/${id}/reject`, { reason });
    toast.success("Rad etildi"); load();
  };
  return (
    <div className="space-y-2" data-testid="admin-withdrawals">
      <div className="flex gap-1">
        {["pending", "approved", "rejected", ""].map((f) => (
          <button key={f || "all"} onClick={() => setFilter(f)} className={`text-xs rounded-full px-3 py-1.5 border ${filter === f ? "bg-foreground text-background" : "bg-card"}`}>{f || "Hammasi"}</button>
        ))}
      </div>
      {list.length === 0 && <p className="text-sm text-muted-foreground">Yo'q</p>}
      {list.map((w) => (
        <div key={w.id} className="rounded-2xl bg-card border border-border p-3" data-testid={`adm-wd-${w.id}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">{w.user?.name || w.user_id?.slice(0, 8)} · <span className="text-foreground">{w.amount?.toLocaleString()} so'm</span></p>
              <p className="text-xs text-muted-foreground font-mono">{w.card_number} · {w.holder_name}</p>
              <p className="text-[10px] text-muted-foreground">{new Date(w.created_at).toLocaleString("uz-UZ")} · {w.status}</p>
            </div>
            {w.status === "pending" && (
              <div className="flex gap-1">
                <button onClick={() => approve(w.id)} className="text-xs rounded-full bg-emerald-600 text-white px-3 py-1.5">✓ Tasdiqlash</button>
                <button onClick={() => reject(w.id)} className="text-xs rounded-full border border-border px-3 py-1.5">✕ Rad</button>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function AdminConcierge() {
  const [list, setList] = useState([]);
  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState("");
  const load = () => api.get("/admin/concierge").then((r) => setList(r.data || []));
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (search.length >= 2) api.get("/admin/users", { params: { q: search } }).then((r) => setUsers(r.data || []));
  }, [search]);
  const addMatch = async (orderId, matchUserId) => {
    const note = prompt("Mos haqida izoh (ixtiyoriy):") || "";
    try {
      await api.post(`/admin/concierge/${orderId}/match`, { match_user_id: matchUserId, note });
      toast.success("Mos qo'shildi");
      load();
    } catch (e) { toast.error("Xato"); }
  };
  return (
    <div className="space-y-3" data-testid="admin-concierge">
      <input placeholder="Foydalanuvchi qidirish (mos qo'shish uchun)..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full rounded-2xl border border-border bg-card px-4 py-3 text-sm" />
      {list.length === 0 && <p className="text-sm text-muted-foreground">Buyurtma yo'q</p>}
      {list.map((o) => (
        <div key={o.id} className="rounded-2xl bg-card border border-border p-3" data-testid={`adm-con-${o.id}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">{o.user?.name || o.user_id?.slice(0, 8)} · {(o.amount || 0).toLocaleString()} so'm</p>
              <p className="text-xs text-muted-foreground">Status: {o.status} · {(o.matches || []).length}/5 mos</p>
            </div>
            <span className={`text-[10px] px-2 py-1 rounded-full ${o.status === "in_progress" ? "bg-amber-100 text-amber-700" : o.status === "completed" ? "bg-emerald-100 text-emerald-700" : "bg-muted text-muted-foreground"}`}>{o.status}</span>
          </div>
          {o.status === "in_progress" && search.length >= 2 && users.length > 0 && (
            <div className="mt-2 max-h-40 overflow-y-auto border-t border-border/40 pt-2 space-y-1">
              <p className="text-[10px] text-muted-foreground">Qidiruv natijasi:</p>
              {users.slice(0, 5).map((u) => (
                <button key={u.id} onClick={() => addMatch(o.id, u.id)} className="w-full text-left text-xs flex items-center gap-2 p-2 rounded-lg hover:bg-muted">
                  <div className="w-6 h-6 rounded-full bg-muted overflow-hidden">
                    {u.photo_url && <img loading="lazy" decoding="async" src={photoSrc(u.photo_url)} alt="" className="w-full h-full object-cover" />}
                  </div>
                  <span className="flex-1 truncate">{u.name} · {u.age} · {u.region}</span>
                  <span className="text-foreground">+ Qo'shish</span>
                </button>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
