import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import { Link } from "react-router-dom";
import { ArrowLeft, ShieldCheck, Wallet, Users as UsersIcon, DollarSign, TrendingUp, BarChart3, LayoutDashboard, Search, MessageSquare, Settings, ChevronRight, Filter, Calendar, MapPin, Phone, Mail, Clock, Activity, AlertTriangle } from "lucide-react";
import { photoSrc } from "@/lib/photo";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from "recharts";

const menuItems = [
  { id: "dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { id: "analytics", icon: BarChart3, label: "Analytics" },
  { id: "users", icon: UsersIcon, label: "Users" },
  { id: "payments", icon: DollarSign, label: "Payments" },
  { id: "verifications", icon: ShieldCheck, label: "Verifications" },
  { id: "withdrawals", icon: Wallet, label: "Withdrawals" },
  { id: "referrals", icon: TrendingUp, label: "Referrals" },
  { id: "messages", icon: MessageSquare, label: "Chat" },
  { id: "concierge", icon: Search, label: "Concierge" },
  { id: "fraud", icon: AlertTriangle, label: "Fraud" },
  { id: "reports", icon: Settings, label: "Reports" },
];

export default function Admin() {
  const { user, t } = useApp();
  const [stats, setStats] = useState(null);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    api.get("/admin/stats").then((r) => setStats(r.data)).catch(() => {});
  }, []);

  if (!user) return null;
  if (!user.is_admin) {
    return <div className="p-8 text-center text-muted-foreground" data-testid="admin-no-access">Faqat admin uchun</div>;
  }

  return (
    <div className="min-h-screen bg-background flex flex-col lg:flex-row">
      {/* Sidebar */}
      <aside className={`lg:fixed lg:left-0 lg:top-0 lg:h-full bg-card border-r border-border transition-all duration-300 z-50 ${sidebarOpen ? "lg:w-64 w-full" : "lg:w-16 w-full"}`}>
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h1 className={`font-heading font-semibold ${sidebarOpen ? "text-xl" : "text-center text-sm"}`}>
            {sidebarOpen ? "Admin Panel" : "AP"}
          </h1>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="lg:hidden p-2 rounded-full hover:bg-muted"
          >
            <ChevronRight className={`w-5 h-5 transition-transform ${sidebarOpen ? "rotate-180" : ""}`} />
          </button>
        </div>
        <nav className="p-2 space-y-1">
          {menuItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors ${
                activeTab === item.id
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted text-muted-foreground hover:text-foreground"
              }`}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {sidebarOpen && <span className="text-sm font-medium">{item.label}</span>}
            </button>
          ))}
        </nav>
        <div className="hidden lg:block absolute bottom-0 left-0 right-0 p-2 border-t border-border">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl hover:bg-muted text-muted-foreground"
          >
            <ChevronRight className={`w-5 h-5 transition-transform ${sidebarOpen ? "rotate-180" : ""}`} />
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className={`flex-1 transition-all duration-300 ${sidebarOpen ? "lg:ml-64" : "lg:ml-16"}`}>
        <div className="p-4 lg:p-6 w-full">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Link to="/me" className="p-2 rounded-full hover:bg-muted">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <h2 className="font-heading text-xl lg:text-2xl font-semibold">{menuItems.find(m => m.id === activeTab)?.label}</h2>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>{user.name}</span>
            </div>
          </div>

          {activeTab === "dashboard" && stats && (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4" data-testid="admin-stats">
              <StatCard label="Users" value={stats.total_users} icon={<UsersIcon className="w-4 h-4" />} />
              <StatCard label="DAU" value={stats.dau} />
              <StatCard label="WAU" value={stats.wau} />
              <StatCard label="Conversion" value={`${stats.conversion_premium}%`} />
              <StatCard label="Premium" value={stats.premium} />
              <StatCard label="VIP" value={stats.vip} />
              <StatCard label="M/F Ratio" value={`${stats.males} / ${stats.females}`} />
              <StatCard label="Revenue" value={`${(stats.revenue?.total || 0).toLocaleString()} so'm`} icon={<DollarSign className="w-4 h-4" />} />
              <StatCard label="Pending Pay" value={stats.pending_payments} />
              <StatCard label="Pending Verif" value={stats.pending_verifications} />
              <StatCard label="Referrals" value={stats.referrals?.total || 0} />
              <StatCard label="Reports" value={stats.open_reports || 0} />
              {stats.quality && (
                <>
                  <StatCard label="Avg Completion" value={`${stats.quality.avg_completion}%`} />
                  <StatCard label="Retention" value={`${stats.quality.retention_rate}%`} />
                  <StatCard label="Msgs/User" value={stats.quality.avg_messages_per_user} />
                </>
              )}
            </div>
          )}

          {activeTab === "analytics" && stats && <AdminAnalytics stats={stats} />}
          {activeTab === "users" && <AdminUsers />}
          {activeTab === "payments" && <AdminPayments />}
          {activeTab === "verifications" && <AdminVerifications />}
          {activeTab === "withdrawals" && <AdminWithdrawals />}
          {activeTab === "referrals" && <AdminReferrals />}
          {activeTab === "messages" && <AdminMessages />}
          {activeTab === "concierge" && <AdminConcierge />}
          {activeTab === "fraud" && <AdminFraud />}
          {activeTab === "reports" && <AdminReports />}
        </div>
      </main>
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

function AdminAnalytics({ stats }) {
  const revenueData = [
    { name: "Bugun", value: stats.revenue?.today || 0 },
    { name: "Hafta", value: stats.revenue?.week || 0 },
    { name: "Oy", value: stats.revenue?.month || 0 },
  ];

  const purposeData = (stats.revenue?.by_purpose || []).map(p => ({
    name: p._id,
    value: p.total,
    count: p.count,
  }));

  const regionData = (stats.top_regions || []).map(r => ({
    name: r._id,
    value: r.count,
  }));

  const genderData = [
    { name: "Erkak", value: stats.males || 0 },
    { name: "Ayol", value: stats.females || 0 },
  ];

  const COLORS = ["hsl(var(--primary))", "hsl(var(--secondary))"];

  return (
    <div className="space-y-6" data-testid="admin-analytics">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="rounded-3xl bg-card border border-border p-4">
          <h3 className="font-heading text-lg mb-4 flex items-center gap-2"><TrendingUp className="w-4 h-4" /> Daromad (so'm)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={revenueData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="hsl(var(--primary))" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-3xl bg-card border border-border p-4">
          <h3 className="font-heading text-lg mb-4 flex items-center gap-2"><UsersIcon className="w-4 h-4" /> Jins nisbati</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={genderData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label>
                {genderData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {purposeData.length > 0 && (
        <div className="rounded-3xl bg-card border border-border p-4">
          <h3 className="font-heading text-lg mb-4">Daromad bo'yicha</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={purposeData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="hsl(var(--secondary))" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {regionData.length > 0 && (
        <div className="rounded-3xl bg-card border border-border p-4">
          <h3 className="font-heading text-lg mb-4 flex items-center gap-2"><MapPin className="w-4 h-4" /> Top hududlar</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={regionData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="hsl(var(--gold))" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="rounded-3xl bg-card border border-border p-4">
        <h3 className="font-heading text-lg mb-4 flex items-center gap-2"><Activity className="w-4 h-4" /> Xabarlar statistikasi</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-muted rounded-2xl">
            <p className="text-sm text-muted-foreground">Jami xabarlar</p>
            <p className="text-2xl font-semibold">{stats.messages?.total?.toLocaleString() || 0}</p>
          </div>
          <div className="p-4 bg-muted rounded-2xl">
            <p className="text-sm text-muted-foreground">Bugun xabarlar</p>
            <p className="text-2xl font-semibold">{stats.messages?.today?.toLocaleString() || 0}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function AdminUsers() {
  const [q, setQ] = useState("");
  const [filters, setFilters] = useState({ gender: "", region: "", age_min: "", age_max: "", marital_status: "" });
  const [list, setList] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [selectedUser, setSelectedUser] = useState(null);
  const [regions, setRegions] = useState([]);
  const [loading, setLoading] = useState(false);
  const limit = 20;
  
  const load = () => {
    setLoading(true);
    const params = { q, page, limit };
    if (filters.gender) params.gender = filters.gender;
    if (filters.region) params.region = filters.region;
    if (filters.marital_status) params.marital_status = filters.marital_status;
    if (filters.age_min) params.age_min = parseInt(filters.age_min);
    if (filters.age_max) params.age_max = parseInt(filters.age_max);
    
    api.get("/admin/users", { params }).then((r) => {
      setList(r.data.users || []);
      setTotal(r.data.total || 0);
    }).catch((e) => {
      console.error("Failed to load users:", e);
      toast.error("Foydalanuvchilarni yuklashda xatolik");
    }).finally(() => setLoading(false));
  };
  
  const loadRegions = () => api.get("/admin/regions").then((r) => {
    setRegions(r.data.regions || []);
  }).catch(() => {});
  
  useEffect(() => { load(); loadRegions(); /* eslint-disable-next-line */ }, []);
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [q, page, filters]);
  
  const patch = async (id, patch) => {
    await api.patch(`/admin/users/${id}`, patch);
    load();
    toast.success("Updated");
  };
  
  return (
    <div className="space-y-4" data-testid="admin-users">
      {/* Search and Filters */}
      <div className="space-y-3">
        <input value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} placeholder="Search by name, email, username..." className="w-full rounded-2xl border border-border bg-card px-4 py-3" data-testid="admin-user-search" />
        <div className="flex flex-wrap gap-2">
          <select value={filters.gender} onChange={(e) => setFilters(f => ({ ...f, gender: e.target.value }))} className="rounded-xl border border-border bg-card px-3 py-2 text-sm min-w-[120px]">
            <option value="">Jins: Hammasi</option>
            <option value="male">Erkak</option>
            <option value="female">Ayol</option>
          </select>
          <select value={filters.marital_status} onChange={(e) => setFilters(f => ({ ...f, marital_status: e.target.value }))} className="rounded-xl border border-border bg-card px-3 py-2 text-sm min-w-[140px]">
            <option value="">Oilaviy holat: Hammasi</option>
            <option value="single">Yolg'iz</option>
            <option value="married">Turmush qurgan</option>
            <option value="divorced">Ajrashgan</option>
            <option value="widowed">Beva</option>
          </select>
          <select value={filters.region} onChange={(e) => setFilters(f => ({ ...f, region: e.target.value }))} className="rounded-xl border border-border bg-card px-3 py-2 text-sm min-w-[150px]">
            <option value="">Hudud: Hammasi</option>
            {regions.map(r => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
          <input type="number" placeholder="Yosh min" value={filters.age_min} onChange={(e) => setFilters(f => ({ ...f, age_min: e.target.value }))} className="rounded-xl border border-border bg-card px-3 py-2 text-sm w-24" />
          <input type="number" placeholder="Yosh max" value={filters.age_max} onChange={(e) => setFilters(f => ({ ...f, age_max: e.target.value }))} className="rounded-xl border border-border bg-card px-3 py-2 text-sm w-24" />
          <button onClick={() => setFilters({ gender: "", region: "", age_min: "", age_max: "", marital_status: "" })} className="text-xs rounded-full border border-border px-3 py-2">Tozalash</button>
        </div>
      </div>

      {loading && (
        <div className="text-center py-8 text-muted-foreground">
          Yuklanmoqda...
        </div>
      )}

      {/* User List */}
      <div className="space-y-2">
        {!loading && list.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            Foydalanuvchilar topilmadi
          </div>
        )}
        {!loading && list.map((u) => (
          <div key={u.id} className="rounded-2xl bg-card border border-border p-4 cursor-pointer hover:border-primary/50 transition-colors" data-testid={`admin-user-${u.id}`} onClick={() => setSelectedUser(u)}>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-muted overflow-hidden flex-shrink-0">
                {u.photo_url && <img loading="lazy" decoding="async" src={photoSrc(u.photo_url)} alt="" className="w-full h-full object-cover" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{u.name} · {u.plan} {u.blocked ? "🚫" : ""}</p>
                <p className="text-xs text-muted-foreground truncate">{u.region} · age {u.age} · {u.gender} · {u.marital_status || "Noma'lum"}</p>
                <p className="text-[10px] text-muted-foreground">{u.email} · {u.phone || "Telefon yo'q"}</p>
              </div>
              <ChevronRight className="w-5 h-5 text-muted-foreground flex-shrink-0" />
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {total > limit && (
        <div className="flex justify-center gap-2 mt-4">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 rounded-full border border-border text-xs disabled:opacity-50">Prev</button>
          <span className="px-3 py-1 text-xs">{page} / {Math.ceil(total / limit)}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / limit)} className="px-3 py-1 rounded-full border border-border text-xs disabled:opacity-50">Next</button>
        </div>
      )}

      {/* User Detail Modal */}
      {selectedUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedUser(null)}>
          <div className="bg-card rounded-3xl border border-border max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-heading text-xl font-semibold">Foydalanuvchi tafsilotlari</h3>
              <button onClick={() => setSelectedUser(null)} className="p-2 rounded-full hover:bg-muted">✕</button>
            </div>
            
            <div className="space-y-4">
              {/* Profile */}
              <div className="flex items-center gap-4 p-4 bg-muted rounded-2xl">
                <div className="w-20 h-20 rounded-full bg-muted overflow-hidden">
                  {selectedUser.photo_url && <img src={photoSrc(selectedUser.photo_url)} alt="" className="w-full h-full object-cover" />}
                </div>
                <div>
                  <p className="font-semibold text-lg">{selectedUser.name}</p>
                  <p className="text-sm text-muted-foreground">{selectedUser.email}</p>
                  <p className="text-sm text-muted-foreground">{selectedUser.phone || "Telefon yo'q"}</p>
                  {selectedUser.telegram_id && <p className="text-sm text-muted-foreground">Telegram ID: {selectedUser.telegram_id}</p>}
                  {selectedUser.telegram_username && <p className="text-sm text-muted-foreground">@{selectedUser.telegram_username}</p>}
                  <p className="text-xs text-muted-foreground mt-1">ID: {selectedUser.id}</p>
                </div>
              </div>

              {/* Personal Info */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Jins</p>
                  <p className="font-medium">{selectedUser.gender}</p>
                </div>
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Yosh</p>
                  <p className="font-medium">{selectedUser.age}</p>
                </div>
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Hudud</p>
                  <p className="font-medium">{selectedUser.region}</p>
                </div>
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Oilaviy holat</p>
                  <p className="font-medium">{selectedUser.marital_status || "Noma'lum"}</p>
                </div>
              </div>

              {/* Device & Session Info */}
              <div className="grid grid-cols-1 gap-4">
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">IP Address</p>
                  <p className="font-medium font-mono text-sm">{selectedUser.ip_address || "Unknown"}</p>
                </div>
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">User Agent</p>
                  <p className="font-medium text-xs break-all">{selectedUser.user_agent || "Unknown"}</p>
                </div>
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Last Active</p>
                  <p className="font-medium text-sm">{selectedUser.last_active ? new Date(selectedUser.last_active).toLocaleString("uz-UZ") : "Unknown"}</p>
                </div>
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Created At</p>
                  <p className="font-medium text-sm">{selectedUser.created_at ? new Date(selectedUser.created_at).toLocaleString("uz-UZ") : "Unknown"}</p>
                </div>
              </div>

              {/* Account Info */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Plan</p>
                  <p className="font-medium">{selectedUser.plan}</p>
                </div>
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Balance</p>
                  <p className="font-medium">{selectedUser.balance?.toLocaleString()} so'm</p>
                </div>
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Referral earnings</p>
                  <p className="font-medium">{selectedUser.referral_earnings_withdrawable?.toLocaleString()} so'm</p>
                </div>
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Influence</p>
                  <p className="font-medium">{selectedUser.influence?.toLocaleString()}</p>
                </div>
              </div>

              {/* Verification Status */}
              <div className="grid grid-cols-3 gap-4">
                <div className={`p-3 rounded-xl ${selectedUser.verified_selfie ? "bg-emerald-100 text-emerald-700" : "bg-muted"}`}>
                  <p className="text-xs">Selfie</p>
                  <p className="font-medium">{selectedUser.verified_selfie ? "✓" : "✕"}</p>
                </div>
                <div className={`p-3 rounded-xl ${selectedUser.verified_identity ? "bg-emerald-100 text-emerald-700" : "bg-muted"}`}>
                  <p className="text-xs">Identity</p>
                  <p className="font-medium">{selectedUser.verified_identity ? "✓" : "✕"}</p>
                </div>
                <div className={`p-3 rounded-xl ${selectedUser.verified_financial ? "bg-emerald-100 text-emerald-700" : "bg-muted"}`}>
                  <p className="text-xs">Financial</p>
                  <p className="font-medium">{selectedUser.verified_financial ? "✓" : "✕"}</p>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 flex-wrap">
                <button onClick={() => patch(selectedUser.id, { verified_selfie: !selectedUser.verified_selfie })} className="text-xs rounded-full bg-secondary/10 text-secondary px-3 py-2">{selectedUser.verified_selfie ? "✓ Selfie" : "Verify selfie"}</button>
                <button onClick={() => patch(selectedUser.id, { verified_financial: !selectedUser.verified_financial })} className="text-xs rounded-full bg-gold-light text-yellow-900 px-3 py-2">{selectedUser.verified_financial ? "💎 Financial" : "Verify financial"}</button>
                <button onClick={() => patch(selectedUser.id, { plan: selectedUser.plan === "premium" ? "free" : "premium" })} className="text-xs rounded-full bg-primary/10 text-foreground px-3 py-2">{selectedUser.plan === "premium" ? "Cancel Premium" : "Make Premium"}</button>
                <button onClick={() => patch(selectedUser.id, { plan: selectedUser.plan === "vip" ? "free" : "vip" })} className="text-xs rounded-full bg-ink text-gold px-3 py-2">{selectedUser.plan === "vip" ? "Cancel VIP" : "Make VIP"}</button>
                <button onClick={() => patch(selectedUser.id, { add_balance: 10000 })} className="text-xs rounded-full border border-border px-3 py-2">+10k</button>
                <button onClick={() => patch(selectedUser.id, { blocked: !selectedUser.blocked })} className={`text-xs rounded-full px-3 py-2 ${selectedUser.blocked ? "bg-emerald-100 text-emerald-700" : "bg-red-50 text-red-700"}`}>{selectedUser.blocked ? "Unblock" : "Block"}</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AdminPayments() {
  const [list, setList] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 20;
  const load = () => api.get("/admin/payments", { params: { page, limit } }).then((r) => {
    setList(r.data.payments || []);
    setTotal(r.data.total || 0);
  });
  useEffect(() => { load(); }, [page]);
  const confirm = async (id) => {
    await api.post(`/payments/admin-confirm/${id}`);
    toast.success("Confirmed");
    load();
  };
  const blockPayment = async (id) => {
    await api.post(`/admin/payments/${id}/block`);
    toast.success("Blocked");
    load();
  };
  const unblockPayment = async (id) => {
    await api.post(`/admin/payments/${id}/unblock`);
    toast.success("Unblocked");
    load();
  };
  return (
    <div className="space-y-2" data-testid="admin-payments">
      {list.map((p) => (
        <div key={p.id} className="rounded-2xl bg-card border border-border p-3" data-testid={`adm-pay-${p.id}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm">{p.purpose} · {p.amount?.toLocaleString()} so'm</p>
              <p className="text-xs text-muted-foreground">{p.status} {p.blocked_by_admin && "🚫 Blocked"}</p>
            </div>
            <div className="flex gap-1">
              {p.status !== "success" && !p.blocked_by_admin && (
                <button data-testid={`adm-pay-confirm-${p.id}`} onClick={() => confirm(p.id)} className="text-xs rounded-full bg-secondary text-white px-3 py-1.5">Confirm</button>
              )}
              {p.blocked_by_admin ? (
                <button onClick={() => unblockPayment(p.id)} className="text-xs rounded-full bg-emerald-100 text-emerald-700 px-3 py-1.5">Unblock</button>
              ) : (
                <button onClick={() => blockPayment(p.id)} className="text-xs rounded-full bg-red-50 text-red-700 px-3 py-1.5">Block</button>
              )}
            </div>
          </div>
        </div>
      ))}
      {total > limit && (
        <div className="flex justify-center gap-2 mt-4">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 rounded-full border border-border text-xs disabled:opacity-50">Prev</button>
          <span className="px-3 py-1 text-xs">{page} / {Math.ceil(total / limit)}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / limit)} className="px-3 py-1 rounded-full border border-border text-xs disabled:opacity-50">Next</button>
        </div>
      )}
    </div>
  );
}

function AdminVerifications() {
  const [list, setList] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 20;
  const load = () => api.get("/admin/verifications", { params: { page, limit } }).then((r) => {
    setList(r.data.verifications || []);
    setTotal(r.data.total || 0);
  });
  useEffect(() => { load(); }, [page]);
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
      {total > limit && (
        <div className="flex justify-center gap-2 mt-4">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 rounded-full border border-border text-xs disabled:opacity-50">Prev</button>
          <span className="px-3 py-1 text-xs">{page} / {Math.ceil(total / limit)}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / limit)} className="px-3 py-1 rounded-full border border-border text-xs disabled:opacity-50">Next</button>
        </div>
      )}
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
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [selectedWithdrawal, setSelectedWithdrawal] = useState(null);
  const limit = 20;
  const load = () => api.get("/admin/withdrawals", { params: { status: filter || undefined, page, limit } }).then((r) => {
    setList(r.data.withdrawals || []);
    setTotal(r.data.total || 0);
  });
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filter, page]);
  const approve = async (id) => { 
    await api.post(`/admin/withdrawals/${id}/approve`); 
    toast.success("Tasdiqlandi"); 
    load(); 
  };
  const reject = async (id) => {
    const reason = prompt("Rad etish sababi:") || "";
    await api.post(`/admin/withdrawals/${id}/reject`, { reason });
    toast.success("Rad etildi"); 
    load();
  };
  return (
    <div className="space-y-4" data-testid="admin-withdrawals">
      <div className="flex gap-1">
        {["pending", "approved", "rejected", ""].map((f) => (
          <button key={f || "all"} onClick={() => { setFilter(f); setPage(1); }} className={`text-xs rounded-full px-3 py-1.5 border ${filter === f ? "bg-foreground text-background" : "bg-card"}`}>{f || "Hammasi"}</button>
        ))}
      </div>
      {list.length === 0 && <p className="text-sm text-muted-foreground">Yo'q</p>}
      <div className="space-y-2">
        {list.map((w) => (
          <div key={w.id} className="rounded-2xl bg-card border border-border p-3 cursor-pointer hover:border-primary/50 transition-colors" data-testid={`adm-wd-${w.id}`} onClick={() => setSelectedWithdrawal(w)}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">{w.user?.name || w.user_id?.slice(0, 8)} · <span className="text-foreground">{w.amount?.toLocaleString()} so'm</span></p>
                <p className="text-xs text-muted-foreground font-mono">{w.card_number} · {w.holder_name}</p>
                <p className="text-[10px] text-muted-foreground">{new Date(w.created_at).toLocaleString("uz-UZ")} · {w.status}</p>
              </div>
              {w.status === "pending" && (
                <div className="flex gap-1">
                  <button onClick={(e) => { e.stopPropagation(); approve(w.id); }} className="text-xs rounded-full bg-emerald-600 text-white px-3 py-1.5">✓ Tasdiqlash</button>
                  <button onClick={(e) => { e.stopPropagation(); reject(w.id); }} className="text-xs rounded-full border border-border px-3 py-1.5">✕ Rad</button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      {total > limit && (
        <div className="flex justify-center gap-2 mt-4">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 rounded-full border border-border text-xs disabled:opacity-50">Prev</button>
          <span className="px-3 py-1 text-xs">{page} / {Math.ceil(total / limit)}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / limit)} className="px-3 py-1 rounded-full border border-border text-xs disabled:opacity-50">Next</button>
        </div>
      )}

      {/* Withdrawal Detail Modal */}
      {selectedWithdrawal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedWithdrawal(null)}>
          <div className="bg-card rounded-3xl border border-border max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-heading text-xl font-semibold">Yechib olish tafsilotlari</h3>
              <button onClick={() => setSelectedWithdrawal(null)} className="p-2 rounded-full hover:bg-muted">✕</button>
            </div>
            
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Summa</p>
                  <p className="font-medium">{selectedWithdrawal.amount?.toLocaleString()} so'm</p>
                </div>
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Status</p>
                  <p className="font-medium">{selectedWithdrawal.status}</p>
                </div>
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Karta raqami</p>
                  <p className="font-medium font-mono">{selectedWithdrawal.card_number}</p>
                </div>
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Karta egasi</p>
                  <p className="font-medium">{selectedWithdrawal.holder_name}</p>
                </div>
              </div>

              {selectedWithdrawal.source_breakdown && selectedWithdrawal.source_breakdown.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Pul manbai (referral daromadlari):</h4>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {selectedWithdrawal.source_breakdown.map((source, idx) => (
                      <div key={idx} className="p-3 bg-muted rounded-xl text-xs">
                        <p className="font-medium">{source.type} · {source.amount?.toLocaleString()} so'm</p>
                        <p className="text-muted-foreground">Referred user: {source.referred_user_id?.slice(0, 8)}</p>
                        <p className="text-muted-foreground">{new Date(source.created_at).toLocaleString("uz-UZ")}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedWithdrawal.status === "paid" && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-muted rounded-xl">
                    <p className="text-xs text-muted-foreground">Soliq (12%)</p>
                    <p className="font-medium">{selectedWithdrawal.tax_amount?.toLocaleString()} so'm</p>
                  </div>
                  <div className="p-3 bg-muted rounded-xl">
                    <p className="text-xs text-muted-foreground">Net summa</p>
                    <p className="font-medium">{selectedWithdrawal.net_amount?.toLocaleString()} so'm</p>
                  </div>
                </div>
              )}

              {selectedWithdrawal.status === "pending" && (
                <div className="flex gap-2">
                  <button onClick={() => { approve(selectedWithdrawal.id); setSelectedWithdrawal(null); }} className="flex-1 text-sm rounded-full bg-emerald-600 text-white px-4 py-2">✓ Tasdiqlash</button>
                  <button onClick={() => { reject(selectedWithdrawal.id); setSelectedWithdrawal(null); }} className="flex-1 text-sm rounded-full border border-border px-4 py-2">✕ Rad</button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
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

function AdminReferrals() {
  const [list, setList] = useState([]);
  const [filter, setFilter] = useState("all");
  const load = () => api.get("/admin/referrals", { params: { type: filter || undefined } }).then((r) => setList(r.data || []));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filter]);
  return (
    <div className="space-y-2" data-testid="admin-referrals">
      <div className="flex gap-1">
        {["all", "signup_free", "paid_subscription", "multi_level_2"].map((f) => (
          <button key={f} onClick={() => setFilter(f)} className={`text-xs rounded-full px-3 py-1.5 border ${filter === f ? "bg-foreground text-background" : "bg-card"}`}>{f}</button>
        ))}
      </div>
      {list.length === 0 && <p className="text-sm text-muted-foreground">Yo'q</p>}
      {list.map((r) => (
        <div key={r.id} className="rounded-2xl bg-card border border-border p-3" data-testid={`adm-ref-${r.id}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">{r.type} · <span className="text-foreground">{r.amount?.toLocaleString()} so'm</span></p>
              <p className="text-xs text-muted-foreground">{r.user_id?.slice(0, 8)} → {r.referred_user_id?.slice(0, 8)}</p>
              <p className="text-[10px] text-muted-foreground">{new Date(r.created_at).toLocaleString("uz-UZ")} · {r.status}</p>
            </div>
            {r.status === "pending" && (
              <span className="text-[10px] px-2 py-1 rounded-full bg-amber-100 text-amber-700">Kutilmoqda</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function AdminMessages() {
  const [list, setList] = useState([]);
  const [q, setQ] = useState("");
  const [userIdFilter, setUserIdFilter] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const limit = 20;
  const load = () => {
    setLoading(true);
    const params = { q, page, limit };
    if (userIdFilter) params.user_id = userIdFilter;
    
    api.get("/admin/messages", { params }).then((r) => {
      setList(r.data.messages || []);
      setTotal(r.data.total || 0);
    }).catch((e) => {
      console.error("Failed to load messages:", e);
      toast.error("Xabarlarni yuklashda xatolik");
    }).finally(() => setLoading(false));
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [q, userIdFilter, page]);
  const deleteMsg = async (id) => {
    if (confirm("Xabarni o'chirmoqchimisiz?")) {
      await api.delete(`/admin/messages/${id}`);
      toast.success("O'chirildi");
      load();
    }
  };
  return (
    <div className="space-y-4" data-testid="admin-messages">
      <div className="space-y-2">
        <input value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} placeholder="Search messages by text..." className="w-full rounded-2xl border border-border bg-card px-4 py-3" />
        <input value={userIdFilter} onChange={(e) => { setUserIdFilter(e.target.value); setPage(1); }} placeholder="Filter by user ID..." className="w-full rounded-2xl border border-border bg-card px-4 py-3" />
      </div>
      
      {loading && (
        <div className="text-center py-8 text-muted-foreground">
          Yuklanmoqda...
        </div>
      )}
      
      {!loading && list.length === 0 && <p className="text-sm text-muted-foreground">Xabarlar topilmadi</p>}
      {!loading && list.map((m) => (
        <div key={m.id} className="rounded-2xl bg-card border border-border p-3" data-testid={`adm-msg-${m.id}`}>
          <div className="flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-8 h-8 rounded-full bg-muted overflow-hidden flex-shrink-0">
                  {m.from_user_photo && <img loading="lazy" decoding="async" src={photoSrc(m.from_user_photo)} alt="" className="w-full h-full object-cover" />}
                </div>
                <p className="text-sm font-medium">{m.from_user_name || "Unknown"}</p>
                <span className="text-muted-foreground">→</span>
                <div className="w-8 h-8 rounded-full bg-muted overflow-hidden flex-shrink-0">
                  {m.to_user_photo && <img loading="lazy" decoding="async" src={photoSrc(m.to_user_photo)} alt="" className="w-full h-full object-cover" />}
                </div>
                <p className="text-sm font-medium">{m.to_user_name || "Unknown"}</p>
              </div>
              <p className="text-sm font-medium truncate">{m.text || "[voice/video]"}</p>
              <p className="text-xs text-muted-foreground">{m.kind} · {new Date(m.created_at).toLocaleString("uz-UZ")}</p>
            </div>
            <button onClick={() => deleteMsg(m.id)} className="text-xs rounded-full bg-red-50 text-red-700 px-2 py-1 flex-shrink-0">O'chirish</button>
          </div>
        </div>
      ))}
      {total > limit && (
        <div className="flex justify-center gap-2 mt-4">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 rounded-full border border-border text-xs disabled:opacity-50">Prev</button>
          <span className="px-3 py-1 text-xs">{page} / {Math.ceil(total / limit)}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / limit)} className="px-3 py-1 rounded-full border border-border text-xs disabled:opacity-50">Next</button>
        </div>
      )}
    </div>
  );
}

function AdminFraud() {
  const [list, setList] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [minScore, setMinScore] = useState(50);
  const limit = 50;
  const load = () => api.get("/admin/fraud", { params: { min_score: minScore, page, limit } }).then((r) => {
    setList(r.data.users || []);
    setTotal(r.data.total || 0);
  });
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [minScore, page]);
  const markSafe = async (uid) => {
    await api.post(`/admin/users/${uid}/mark-safe`);
    toast.success("Marked as safe");
    load();
  };
  return (
    <div className="space-y-4" data-testid="admin-fraud">
      <div className="flex gap-2 items-center">
        <label className="text-sm">Min fraud score:</label>
        <input type="number" value={minScore} onChange={(e) => { setMinScore(Number(e.target.value)); setPage(1); }} className="rounded-xl border border-border bg-card px-3 py-2 text-sm w-24" />
      </div>
      {list.length === 0 && <p className="text-sm text-muted-foreground">No suspicious users found</p>}
      <div className="space-y-2">
        {list.map((u) => (
          <div key={u.id} className="rounded-2xl bg-card border border-border p-3" data-testid={`adm-fraud-${u.id}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-muted overflow-hidden">
                  {u.photo_url && <img loading="lazy" decoding="async" src={photoSrc(u.photo_url)} alt="" className="w-full h-full object-cover" />}
                </div>
                <div>
                  <p className="text-sm font-medium">{u.name} · Score: {u.fraud_score || 0}</p>
                  <p className="text-xs text-muted-foreground">{u.email} · {u.ip_address || "Unknown IP"}</p>
                  {u.fraud_reasons && u.fraud_reasons.length > 0 && (
                    <p className="text-[10px] text-red-600">{u.fraud_reasons.join(", ")}</p>
                  )}
                </div>
              </div>
              <div className="flex gap-1">
                {u.flagged_as_bot && <span className="text-[10px] px-2 py-1 rounded-full bg-red-100 text-red-700">🤖 Bot</span>}
                <button onClick={() => markSafe(u.id)} className="text-xs rounded-full bg-emerald-100 text-emerald-700 px-2 py-1">Mark Safe</button>
              </div>
            </div>
          </div>
        ))}
      </div>
      {total > limit && (
        <div className="flex justify-center gap-2 mt-4">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 rounded-full border border-border text-xs disabled:opacity-50">Prev</button>
          <span className="px-3 py-1 text-xs">{page} / {Math.ceil(total / limit)}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / limit)} className="px-3 py-1 rounded-full border border-border text-xs disabled:opacity-50">Next</button>
        </div>
      )}
    </div>
  );
}
