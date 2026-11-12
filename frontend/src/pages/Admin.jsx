import React, { useState } from "react";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import { ShieldCheck, Wallet, Users as UsersIcon, DollarSign, TrendingUp, BarChart3, LayoutDashboard, Search, MessageSquare, Settings, ChevronRight, MapPin, Activity, AlertTriangle, Send, Megaphone, Trash2, Bot, Eye, Pencil, Link2, Heart, Crown, Gauge, ScrollText, Ban, VolumeX, EyeOff, Menu, X, Gift, PackageOpen } from "lucide-react";
import { photoSrc } from "@/lib/photo";
import { FEATURES } from "@/lib/features";
import api from "@/lib/api";
import { PURPOSE_UZ, REF_TYPE_UZ, VERIF_KIND_UZ } from "@/lib/labels";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from "recharts";
import { useQueryClient } from "@tanstack/react-query";
import {
  useAdminAnnouncements,
  useAdminStats, useAdminUsers, useAdminRegions, useAdminUserSearch, useUpdateAdminUser,
  useAdminPayments, useAdminPaymentBlock, useAdminVerifications, useAdminDecideVerification,
  useAdminReports, useAdminWithdrawals, useAdminWithdrawalDecision, useAdminConcierge,
  useAdminConciergeMatch, useAdminReferrals, useAdminReferrers, useAdminReferrerDetail, useAdminMessages, useAdminDeleteMessage,
  useAdminFraud, useAdminMarkSafe, useAdminBroadcast,
  useAdminCeo, useAdminFunnel, useAdminEngagement, useAdminRevenue,
  useAdminConciergeAnalytics, useAdminChatModAnalytics, useAdminAuditLog, useAdminGiftShop,
  useAdminUserDetail, useAdminUserAction, useDeleteDemoUsers, useAdminConfigHealth,
  useAdminAiInsights, useAdminAiInsightsCached, useRefreshAiInsights,
} from "@/hooks/queries";

// Eight places instead of nineteen: related screens are grouped and shown as
// sub-tabs, so an admin finds "where do I approve X" without scanning a list.
const SECTIONS = [
  { id: "home", icon: Gauge, label: "Bosh sahifa" },
  { id: "users", icon: UsersIcon, label: "Foydalanuvchilar" },
  { id: "moderation", icon: ShieldCheck, label: "Moderatsiya", subs: [
    { id: "verifications", label: "Tasdiqlashlar" },
    { id: "reports", label: "Shikoyatlar" },
    { id: "messages", label: "Chat nazorati" },
    { id: "fraud", label: "Firibgarlik" },
  ] },
  { id: "money", icon: Wallet, label: "Pul", subs: [
    { id: "payments", label: "To'lovlar" },
    { id: "p2p", label: "To'lov tizimi" },
    { id: "withdrawals", label: "Pul yechish" },
    { id: "referrals", label: "Referallar" },
  ] },
  { id: "insights", icon: BarChart3, label: "Tahlil", subs: [
    { id: "ai", label: "AI tahlil" },
    { id: "ceo", label: "Ko'rsatkichlar" },
    { id: "growth", label: "Voronka" },
    { id: "revenue", label: "Daromad" },
    ...(FEATURES.giftShop ? [{ id: "giftshop", label: "Sovg'alar" }] : []),
  ] },
  { id: "comms", icon: Megaphone, label: "Aloqa", subs: [
    { id: "broadcast", label: "Xabar yuborish" },
    { id: "anons", label: "Anonslar" },
  ] },
  { id: "concierge", icon: Search, label: "Shaxsiy sovchi" },
  { id: "auditlog", icon: ScrollText, label: "Admin harakatlari" },
];
const sectionOf = (tab) => SECTIONS.find((sec) => sec.id === tab || (sec.subs || []).some((x) => x.id === tab)) || SECTIONS[0];
// Pending work per section, shown as a badge so nothing waits unseen.
const sectionBadge = (secId, stats) => {
  if (!stats) return 0;
  if (secId === "moderation") return (stats.pending_verifications || 0) + (stats.open_reports || 0);
  if (secId === "money") return (stats.pending_topups || 0) + (stats.pending_withdrawals || 0);
  if (secId === "concierge") return stats.pending_concierge || 0;
  return 0;
};

// Human labels for stored status / action codes (admins should never read raw keys).
const STATUS_UZ = {
  pending: "Kutilmoqda", approved: "Tasdiqlangan", rejected: "Rad etilgan", paid: "To'langan",
  completed: "Yakunlangan", in_progress: "Jarayonda", awaiting_payment: "To'lov kutilmoqda",
  cancelled: "Bekor qilingan", resolved: "Hal qilingan", open: "Ochiq", new: "Yangi",
};
const statusUz = (s) => STATUS_UZ[s] || s || "—";
const ACTION_UZ = {
  update_user: "Foydalanuvchini o'zgartirdi", set_women_free: "Ayollar uchun bepul Premium'ni o'zgartirdi", delete_demo_users: "Demo profillarni o'chirdi",
  give_premium: "Premium berdi", give_vip: "VIP berdi", give_standard: "Standard berdi",
  reset_balance: "Balansni tozaladi", reset_likes: "Like'larni tozaladi", mute: "Ovozini o'chirdi",
  unmute: "Ovozini yoqdi", shadow_ban: "Yashirin ban", unshadow_ban: "Yashirin bandan chiqardi",
  ban: "Ban qildi", fraud_block: "Firibgarlik uchun blokladi", delete_message: "Xabarni o'chirdi",
  approve_verification: "Tasdiqlashni qabul qildi", reject_verification: "Tasdiqlashni rad etdi",
  approve_withdrawal: "Pul yechishni tasdiqladi", reject_withdrawal: "Pul yechishni rad etdi",
  p2p_topup_approve: "Karta to'ldirishini tasdiqladi", p2p_topup_reject: "Karta to'ldirishini rad etdi",
  broadcast: "Xabar yubordi",
};
const actionUz = (a) => { const k = String(a || "").replace(/^user_action:/, ""); return ACTION_UZ[k] || k; };
const FIELD_UZ = { women_free: "Ayollar uchun bepul",
  verified_identity: "shaxs", verified_selfie: "selfie", verified_financial: "moliyaviy", add_balance: "balansga qo'shildi",
  plan: "tarif", blocked: "blok", count: "soni", target_ids: "kimlar", days: "kun", amount: "summa", topup_id: "so'rov",
};
const genderUz = (g) => ({ male: "Erkak", female: "Ayol" }[g] || g || "—");
const maritalUz = (m) => ({ single: "Turmush qurmagan", divorced: "Ajrashgan", widowed: "Beva" }[m] || m || "Noma'lum");
const planUz = (p) => ({ free: "Bepul", premium: "Premium", vip: "Premium (eski VIP)", standard: "Standard (eski)" }[p] || p || "—");

function AdminPagination({ page, setPage, total, limit }) {
  if (total <= limit) return null;
  return (
    <div className="flex justify-center gap-2 mt-4">
      <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 rounded-full border border-border text-xs disabled:opacity-50">Oldingi</button>
      <span className="px-3 py-1 text-xs">{page} / {Math.ceil(total / limit)}</span>
      <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / limit)} className="px-3 py-1 rounded-full border border-border text-xs disabled:opacity-50">Keyingi</button>
    </div>
  );
}

export default function Admin() {
  const { user, t } = useApp();
  const [activeTab, setActiveTab] = useState("home");
  const section = sectionOf(activeTab);
  const openSection = (sec) => setActiveTab(sec.subs ? sec.subs[0].id : sec.id);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { data: stats } = useAdminStats();
  const { data: configHealth } = useAdminConfigHealth();

  if (!user) return null;
  if (!user.is_admin) {
    return <div className="p-8 text-center text-muted-foreground" data-testid="admin-no-access">Faqat admin uchun</div>;
  }

  return (
    <div className="min-h-screen bg-background flex flex-col lg:flex-row">
      {/* Desktop sidebar - below lg this used to render as a full-width
          block ABOVE the page content (every tab required scrolling past
          all 18 menu buttons first), and its collapse toggle did nothing on
          mobile since both the open/closed classes resolved to the same
          "w-full". Now genuinely desktop-only; mobile gets its own compact
          horizontal tab bar below instead of a shrunk version of this. */}
      <aside className={`hidden lg:flex lg:flex-col lg:fixed lg:left-0 lg:top-0 lg:h-full bg-card border-r border-border transition-all duration-300 z-50 ${sidebarOpen ? "lg:w-64" : "lg:w-16"}`}>
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h1 className={`font-heading font-semibold ${sidebarOpen ? "text-xl" : "text-center text-sm"}`}>
            {sidebarOpen ? "Boshqaruv paneli" : "BP"}
          </h1>
        </div>
        <nav className="p-2 space-y-1">
          {SECTIONS.map((item) => {
            const badge = sectionBadge(item.id, stats);
            return (
              <button
                key={item.id}
                onClick={() => openSection(item)}
                data-testid={`admin-tab-${item.id}`}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors ${
                  section.id === item.id
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-muted text-muted-foreground hover:text-foreground"
                }`}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                {sidebarOpen && <span className="text-sm font-medium flex-1 text-left">{item.label}</span>}
                {sidebarOpen && badge > 0 && <span className="min-w-[20px] h-5 px-1.5 grid place-items-center rounded-full bg-rose-500 text-white text-[11px] font-bold">{badge}</span>}
              </button>
            );
          })}
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

      {/* Mobile: a hamburger opens the full menu as a slide-out drawer,
          instead of a left-to-right scrollable pill strip - with 19
          sections, a horizontal scroll hid most of them off-screen and
          looked cluttered; a drawer shows the whole list at once, exactly
          like the desktop sidebar. This is also the ONLY navigation surface
          inside the admin Mini App - there is deliberately no link back
          into the regular Fidem app (see the removed "/me" back-arrow
          below), so opening the admin bot can never land on the dating app. */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex" role="dialog" aria-modal="true">
          <div className="w-72 max-w-[80vw] h-full bg-card overflow-y-auto shadow-xl">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h1 className="font-heading text-lg font-semibold">Boshqaruv paneli</h1>
              <button onClick={() => setMobileMenuOpen(false)} className="p-2 rounded-full hover:bg-muted" data-testid="admin-mobile-menu-close">
                <X className="w-5 h-5" />
              </button>
            </div>
            <nav className="p-2 space-y-1">
              {SECTIONS.map((item) => {
                const badge = sectionBadge(item.id, stats);
                return (
                  <button
                    key={item.id}
                    onClick={() => { openSection(item); setMobileMenuOpen(false); }}
                    data-testid={`admin-mobile-tab-${item.id}`}
                    className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl transition-colors ${
                      section.id === item.id
                        ? "bg-primary text-primary-foreground"
                        : "hover:bg-muted text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <item.icon className="w-5 h-5 flex-shrink-0" />
                    <span className="text-sm font-medium flex-1 text-left">{item.label}</span>
                    {badge > 0 && <span className="min-w-[20px] h-5 px-1.5 grid place-items-center rounded-full bg-rose-500 text-white text-[11px] font-bold">{badge}</span>}
                  </button>
                );
              })}
            </nav>
          </div>
          <div className="flex-1 bg-black/40" onClick={() => setMobileMenuOpen(false)} />
        </div>
      )}

      {/* Main Content */}
      <main className={`flex-1 transition-all duration-300 ${sidebarOpen ? "lg:ml-64" : "lg:ml-16"}`}>
        <div className="p-4 lg:p-6 w-full">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-6">
            <div className="flex items-center gap-3 min-w-0">
              <button
                onClick={() => setMobileMenuOpen(true)}
                className="lg:hidden p-2 rounded-full hover:bg-muted shrink-0"
                data-testid="admin-mobile-menu-open"
              >
                <Menu className="w-5 h-5" />
              </button>
              <h2 className="font-heading text-xl lg:text-2xl font-semibold truncate">{section.label}</h2>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground shrink-0">
              {configHealth && activeTab === "home" && (
                <span
                  data-testid="admin-bot-status"
                  title={configHealth.admin_bot_configured && !configHealth.admin_bot_token_valid ? "ADMIN_BOT_TOKEN o'rnatilgan, lekin Telegram uni qabul qilmadi - qiymatni qayta tekshiring (bo'sh joy, kesilgan token bo'lishi mumkin)" : undefined}
                  className={`text-[11px] px-2.5 py-1 rounded-full font-medium whitespace-nowrap ${
                    !configHealth.admin_bot_configured
                      ? "bg-muted text-muted-foreground"
                      : configHealth.admin_bot_token_valid
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-rose-100 text-rose-800"
                  }`}
                >
                  {!configHealth.admin_bot_configured
                    ? "🛠 Admin bot: sozlanmagan"
                    : configHealth.admin_bot_token_valid
                      ? `🛠 Admin bot: ulandi${configHealth.admin_bot_username ? ` (@${configHealth.admin_bot_username})` : ""}`
                      : "⚠️ Admin bot: token noto'g'ri"}
                </span>
              )}
              <span className="hidden sm:inline">{user.name}</span>
            </div>
          </div>

          {section.subs && (
            <div className="flex flex-wrap gap-1.5 mb-5" data-testid="admin-subtabs">
              {section.subs.map((x) => (
                <button
                  key={x.id}
                  onClick={() => setActiveTab(x.id)}
                  data-testid={`admin-sub-${x.id}`}
                  className={`rounded-full px-3.5 py-1.5 text-xs font-medium border transition ${
                    activeTab === x.id ? "bg-foreground text-background border-foreground" : "bg-card border-border hover:bg-muted"
                  }`}
                >
                  {x.label}
                </button>
              ))}
            </div>
          )}

          {configHealth && !configHealth.telegram_configured && activeTab === "home" && (
            <details
              data-testid="admin-telegram-not-configured"
              className="mb-6 rounded-2xl bg-rose-50 border border-rose-300 p-4"
            >
              <summary className="cursor-pointer text-sm font-semibold text-rose-900 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" /> Admin Telegram bildirishnomalari o'chiq (batafsil)
              </summary>
            <div className="mt-3 flex gap-3 items-start">
              <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div className="text-sm text-rose-900">
                <p className="font-semibold">Admin Telegram bildirishnomalari o'chiq — hech kimga xabar bormaydi</p>
                <p className="text-rose-800 mt-1 leading-relaxed">
                  Yangi karta to'lovi so'rovlari, /stats va kunlik hisobot Telegram orqali hech kimga yetib bormaydi,
                  chunki <code className="bg-rose-100 px-1 rounded">ADMIN_TELEGRAM_IDS</code> muhit o'zgaruvchisida
                  haqiqiy admin ID topilmadi. Tuzatish uchun:
                </p>
                <ol className="list-decimal list-inside text-rose-800 mt-1.5 space-y-0.5">
                  <li>Telegram'da <b>@userinfobot</b>ga yozing — u sizga shaxsiy ID raqamingizni yuboradi</li>
                  <li>Railway (yoki serveringiz) sozlamalarida <code className="bg-rose-100 px-1 rounded">ADMIN_TELEGRAM_IDS</code> o'zgaruvchisiga o'sha raqamni qo'ying — bot tokenidagi raqam emas, aynan shaxsiy ID</li>
                  <li>Serverni qayta ishga tushiring</li>
                </ol>
              </div>
            </div>
            </details>
          )}

          {activeTab === "home" && <AdminHome stats={stats} go={setActiveTab} />}
          {activeTab === "ceo" && <AdminCeoDashboard go={setActiveTab} />}
          {activeTab === "ai" && <AdminAiInsights />}
          {activeTab === "growth" && <AdminGrowthDashboard />}
          {activeTab === "revenue" && <AdminRevenueDashboard />}
          {activeTab === "giftshop" && <AdminGiftShopDashboard />}
          {activeTab === "auditlog" && <AdminAuditLog />}

          {activeTab === "users" && <AdminUsers />}
          {activeTab === "broadcast" && <AdminBroadcast />}
          {activeTab === "anons" && <AdminAnnouncements />}
          {activeTab === "payments" && <AdminPayments />}
          {activeTab === "p2p" && <AdminManualTopups />}
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

function RevenueTile({ label, value, accent }) {
  return (
    <div className={`rounded-3xl border p-4 ${accent ? "bg-gradient-to-br from-primary/10 to-card border-primary/30" : "bg-card border-border"}`}>
      <p className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="font-heading text-xl font-semibold mt-1 tabular-nums">{value}</p>
    </div>
  );
}

function KpiTile({ label, value, sub, accent }) {
  return (
    <div className={`rounded-2xl border p-3.5 ${accent ? "bg-gradient-to-br from-primary/10 to-card border-primary/30" : "bg-card border-border"}`}>
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground leading-tight">{label}</p>
      <p className="font-heading text-lg font-semibold mt-1 tabular-nums leading-none">{value}</p>
      {sub != null && <p className="text-[10px] text-muted-foreground mt-1">{sub}</p>}
    </div>
  );
}

const sumFmt = (n) => `${Number(n || 0).toLocaleString()} so'm`;

// The CEO Dashboard: the four questions an owner asks every morning —
// how many people came, how many matched, how many chatted, how much money
// came in — answered in one screen, no digging through operator tabs.
// Home: what needs a decision today (each card opens the exact queue), today's
// numbers, and the AI analyst's one-paragraph verdict - the three things an
// owner checks first. Detailed metrics live under Tahlil.
function AdminHome({ stats, go }) {
  const { data: ceo } = useAdminCeo();
  const { data: ai } = useAdminAiInsightsCached();
  const { data: health } = useAdminConfigHealth();
  const aiState = health?.ai;
  const queue = [
    { tab: "verifications", label: "Tasdiqlash kutmoqda", value: stats?.pending_verifications || 0, Icon: ShieldCheck },
    { tab: "reports", label: "Ochiq shikoyatlar", value: stats?.open_reports || 0, Icon: AlertTriangle },
    { tab: "p2p", label: "Karta to'lovi tekshiruvi", value: stats?.pending_topups || 0, Icon: Wallet },
    { tab: "withdrawals", label: "Pul yechish so'rovlari", value: stats?.pending_withdrawals || 0, Icon: DollarSign },
    { tab: "concierge", label: "Sovchi buyurtmalari", value: stats?.pending_concierge || 0, Icon: Search },
  ];
  const todo = queue.filter((q) => q.value > 0);
  return (
    <div className="space-y-6" data-testid="admin-home">
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Bugun qilinadigan ishlar</p>
        {todo.length === 0 ? (
          <div className="rounded-3xl border border-emerald-200 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-300 p-4 text-sm font-medium" data-testid="admin-queue-empty">
            ✓ Hammasi joyida — kutib turgan so'rov yo'q
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {todo.map((q) => (
              <button key={q.tab} onClick={() => go(q.tab)} data-testid={`admin-queue-${q.tab}`}
                className="rounded-2xl border border-primary/40 bg-primary/5 p-4 text-left flex items-center justify-between hover:-translate-y-0.5 transition">
                <span className="flex items-center gap-2.5 text-sm font-medium"><q.Icon className="w-4 h-4 text-primary" /> {q.label}</span>
                <span className="flex items-center gap-1 font-heading text-xl text-primary">{q.value} <ChevronRight className="w-4 h-4" /></span>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-3xl bg-gradient-to-br from-ink to-zinc-800 text-white p-5">
        <p className="text-xs uppercase tracking-wider text-white/60">Bugun</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3">
          {[
            ["Yangi foydalanuvchi", ceo?.users?.new_today],
            ["Faol (bugun)", ceo?.active?.dau ?? stats?.dau],
            ["Matchlar", ceo?.matches?.today],
            ["Daromad", ceo ? sumFmt(ceo.revenue?.today) : undefined],
          ].map(([label, v]) => (
            <div key={label}>
              <p className="text-[10px] text-white/60">{label}</p>
              <p className="font-heading text-2xl font-bold tabular-nums mt-0.5">{v ?? "—"}</p>
            </div>
          ))}
        </div>
        <div className="mt-4 pt-3 border-t border-white/10 grid grid-cols-3 gap-3 text-[11px] text-white/70">
          <span>Jami: <b className="text-white">{(stats?.total_users || 0).toLocaleString()}</b></span>
          <span>Oylik faol: <b className="text-white">{stats?.mau ?? "—"}</b></span>
          <span>Premium: <b className="text-white">{(stats?.premium || 0) + (stats?.vip || 0)}</b></span>
        </div>
      </div>

      <button onClick={() => go("ai")} data-testid="admin-home-ai" className="w-full text-left rounded-3xl bg-card border border-border p-4 hover:border-primary/40 transition">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5"><Bot className="w-3.5 h-3.5" /> AI xulosasi</p>
          {aiState?.checked && (
            <span data-testid="admin-ai-status" className={`text-[10px] font-semibold rounded-full px-2 py-0.5 ${aiState.ok ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}`}>
              {aiState.ok ? "AI ishlayapti" : "AI ishlamayapti"}
            </span>
          )}
        </div>
        {aiState?.checked && !aiState.ok && <p className="text-[11px] text-rose-700 mt-1">Sabab: {aiState.error}</p>}
        {ai?.ai_generated ? (
          <>
            <p className="text-sm mt-2 leading-relaxed line-clamp-3">{ai.summary}</p>
            {ai.recommendations?.[0] && <p className="text-xs text-primary mt-2">👉 {ai.recommendations[0]}</p>}
          </>
        ) : (
          <p className="text-sm text-muted-foreground mt-2">{ai?.error ? `AI tahlil ishlamayapti: ${ai.error}` : ai?.empty ? "Hali tahlil qilinmagan — ochib, AI tahlilini boshlang" : "Yuklanmoqda..."}</p>
        )}
        <p className="text-xs font-semibold text-primary mt-2">Batafsil →</p>
      </button>
    </div>
  );
}

function AdminCeoDashboard({ go }) {
  const { data, isLoading } = useAdminCeo();
  if (isLoading || !data) return <div className="text-center py-12 text-muted-foreground">Yuklanmoqda...</div>;
  const { revenue, users, active, matches, chats, monetization, retention } = data;

  return (
    <div className="space-y-6">
      <div className="rounded-3xl bg-gradient-to-br from-ink to-zinc-800 text-white p-5">
        <p className="text-xs uppercase tracking-wider text-white/60">Bugun</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3">
          <div>
            <p className="text-[10px] text-white/60">Yangi foydalanuvchilar</p>
            <p className="font-heading text-2xl font-bold tabular-nums mt-0.5">{users.new_today}</p>
          </div>
          <div>
            <p className="text-[10px] text-white/60">Matchlar</p>
            <p className="font-heading text-2xl font-bold tabular-nums mt-0.5">{matches.today}</p>
          </div>
          <div>
            <p className="text-[10px] text-white/60">Yangi suhbatlar</p>
            <p className="font-heading text-2xl font-bold tabular-nums mt-0.5">{chats.new_today}</p>
          </div>
          <div>
            <p className="text-[10px] text-white/60">Daromad</p>
            <p className="font-heading text-2xl font-bold tabular-nums mt-0.5 text-gold">{sumFmt(revenue.today)}</p>
          </div>
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Daromad</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <KpiTile label="Bugun" value={sumFmt(revenue.today)} accent />
          <KpiTile label="Bu hafta" value={sumFmt(revenue.week)} />
          <KpiTile label="Bu oy" value={sumFmt(revenue.month)} />
          <KpiTile label="Jami" value={sumFmt(revenue.total)} />
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Faol foydalanuvchilar</p>
        <div className="grid grid-cols-3 gap-2.5">
          <KpiTile label="Bugun faol" value={active.dau} />
          <KpiTile label="Hafta faol" value={active.wau} />
          <KpiTile label="Oy faol" value={active.mau} />
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Match va Chat</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <KpiTile label="Match (bugun)" value={matches.today} sub={matches.match_rate_today_pct != null ? `${matches.match_rate_today_pct}% yangi foydalanuvchidan` : null} />
          <KpiTile label="Match (hafta)" value={matches.week} />
          <KpiTile label="Match (oy)" value={matches.month} />
          <KpiTile label="Suhbatga o'tish" value={chats.chat_rate_today_pct != null ? `${chats.chat_rate_today_pct}%` : "—"} sub="matchdan yozishmagacha" />
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Monetizatsiya</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <KpiTile label="To'lovchilar ulushi" value={`${monetization.premium_conversion_pct}%`} sub={`${monetization.paying_users} to'lovchi`} />
          <KpiTile label="O'rtacha daromad / foydalanuvchi" value={sumFmt(monetization.arpu)} />
          <KpiTile label="O'rtacha daromad / to'lovchi" value={sumFmt(monetization.arppu)} />
          <KpiTile label="Oylik obuna daromadi" value={sumFmt(monetization.mrr)} sub="faol obunalar" />
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Saqlanish</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
          <KpiTile label="Ertasi kuni qaytganlar" value={retention.d1_pct != null ? `${retention.d1_pct}%` : "—"} sub={`${retention.d1_cohort_size} kishidan`} />
        </div>
        {retention.note && <p className="text-[11px] text-muted-foreground mt-2">{retention.note}</p>}
      </div>


    </div>
  );
}

const TREND_UZ = {
  growing: { label: "O'sish kuzatilmoqda", cls: "bg-emerald-100 text-emerald-800" },
  stable: { label: "Barqaror", cls: "bg-amber-100 text-amber-800" },
  declining: { label: "Pasaymoqda", cls: "bg-rose-100 text-rose-800" },
};

// AI growth/activity analyst: reads the exact same numbers the CEO Dashboard
// shows (plus 7d/30d trend + winback effectiveness) and turns them into a
// plain-Uzbek verdict + prioritized recommendations, server-cached for 3h so
// opening this tab doesn't burn a model call every time.
function AdminAiInsights() {
  const { data, isLoading } = useAdminAiInsights();
  const refresh = useRefreshAiInsights();

  if (isLoading) return <div className="text-center py-12 text-muted-foreground">Yuklanmoqda...</div>;

  const trend = TREND_UZ[data?.trend] || TREND_UZ.stable;
  const generatedAt = data?.generated_at ? new Date(data.generated_at).toLocaleString("uz-UZ") : null;

  return (
    <div className="space-y-5">
      <div className="rounded-3xl bg-gradient-to-br from-ink to-zinc-800 text-white p-5">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-primary" />
            <p className="text-xs uppercase tracking-wider text-white/60">AI o'sish tahlilchisi</p>
          </div>
          <span className={`text-[11px] px-2.5 py-1 rounded-full font-semibold ${trend.cls}`}>{trend.label}</span>
        </div>
        <p className="mt-3 text-sm leading-relaxed">
          {data?.ai_generated ? (data.summary || "—") : "AI tahlil hozircha mavjud emas."}
        </p>
        {!data?.ai_generated && data?.error && (
          <p className="mt-2 text-xs text-rose-300">Sabab: {data.error}</p>
        )}
      </div>

      {data?.ai_generated && (
        <>
          {data.highlights?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Diqqatga sazovor</p>
              <div className="space-y-2">
                {data.highlights.map((h, i) => (
                  <div key={i} className="rounded-2xl border border-border bg-card p-3 text-sm">✨ {h}</div>
                ))}
              </div>
            </div>
          )}
          {data.risks?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Xavflar</p>
              <div className="space-y-2">
                {data.risks.map((r, i) => (
                  <div key={i} className="rounded-2xl border border-rose-200 bg-rose-50 text-rose-900 p-3 text-sm">⚠️ {r}</div>
                ))}
              </div>
            </div>
          )}
          {data.recommendations?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Tavsiyalar</p>
              <div className="space-y-2">
                {data.recommendations.map((r, i) => (
                  <div key={i} className="rounded-2xl border border-primary/30 bg-primary/5 p-3 text-sm">👉 {r}</div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      <div className="flex items-center justify-between gap-3 pt-1">
        <p className="text-[11px] text-muted-foreground">{generatedAt ? `So'nggi yangilanish: ${generatedAt}` : ""}</p>
        <button
          onClick={() => refresh.mutate()}
          disabled={refresh.isPending}
          className="text-xs rounded-full bg-primary text-primary-foreground px-4 py-2 font-semibold disabled:opacity-50"
        >
          {refresh.isPending ? "Tahlil qilinmoqda..." : "🔄 Qayta tahlil qilish"}
        </button>
      </div>
    </div>
  );
}

// Growth Dashboard: the acquisition->activation->engagement funnel, plus
// like/match/chat KPI cards — the dating-app-specific numbers a generic
// SaaS dashboard never shows.
// Funnel steps with percentages that make sense: the start is the first step
// that actually has people (Telegram /start is not tracked for everyone), and
// "next" is the share of the previous step that reached this one.
function funnelSteps(raw) {
  const all = raw || [];
  const first = all.findIndex((x) => x.count > 0);
  const steps = first > 0 ? all.slice(first) : all;
  const base = steps[0]?.count || 0;
  return steps.map((x, i) => ({
    ...x,
    top: base ? Math.round((x.count / base) * 100) : 0,
    next: i > 0 && steps[i - 1].count ? Math.round((x.count / steps[i - 1].count) * 100) : 0,
  }));
}

function AdminGrowthDashboard() {
  const { data: funnel, isLoading: fLoading } = useAdminFunnel();
  const { data: eng, isLoading: eLoading } = useAdminEngagement();

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Foydalanuvchi yo'li (voronka)</p>
        {fLoading || !funnel ? (
          <div className="text-center py-8 text-muted-foreground">Yuklanmoqda...</div>
        ) : (
          <div className="rounded-3xl bg-card border border-border p-4 space-y-1.5">
            {funnelSteps(funnel.steps).map((s, i, steps) => (
              <div key={s.key}>
                <div className="flex items-center justify-between text-sm py-2">
                  <span className="font-medium">{i + 1}. {s.label}</span>
                  <span className="tabular-nums">
                    <strong>{s.count.toLocaleString()}</strong>
                    <span className="text-muted-foreground text-xs ml-2">({s.top}% boshidan)</span>
                  </span>
                </div>
                <div className="h-2 rounded-full bg-muted overflow-hidden">
                  <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${s.top}%` }} />
                </div>
                {i < steps.length - 1 && s.count > 0 && (
                  <p className="text-[10px] text-red-500 mt-1 mb-1">
                    ↓ keyingi bosqichga {steps[i + 1].next}% o'tdi
                    {s.count > steps[i + 1].count && ` · ${(s.count - steps[i + 1].count).toLocaleString()} kishi to'xtadi`}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {eLoading || !eng ? (
        <div className="text-center py-8 text-muted-foreground">Yuklanmoqda...</div>
      ) : (
        <>
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Yoqtirishlar</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <KpiTile label="Bugun" value={eng.likes.today} />
              <KpiTile label="Bu hafta" value={eng.likes.week} />
              <KpiTile label="Bu oy" value={eng.likes.month} />
              <KpiTile label="O'zaro (hafta)" value={eng.likes.mutual_this_week} sub="= match" />
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Matchlar</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <KpiTile label="Bugun" value={eng.matches.today} />
              <KpiTile label="Bu hafta" value={eng.matches.week} />
              <KpiTile label="Bu oy" value={eng.matches.month} />
              <KpiTile label="O'rtacha/user" value={eng.matches.avg_per_user} />
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Suhbatlar</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
              <KpiTile label="Yangi suhbatlar (bugun)" value={eng.chats.new_today} />
              <KpiTile label="Faol chatlar (hafta)" value={eng.chats.active_this_week} />
              <KpiTile label="Xabarlar (bugun)" value={eng.chats.messages_today} />
              <KpiTile label="Javob berish %" value={eng.chats.reply_rate_pct != null ? `${eng.chats.reply_rate_pct}%` : "—"} />
              <KpiTile label="O'rtacha xabar/chat" value={eng.chats.avg_messages_per_chat} />
              <KpiTile label="Xabarlar (hafta)" value={eng.chats.messages_week} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// Revenue Dashboard: REAL cash in (CLICK-completed + approved P2P — never
// double-counts a balance-funded purchase that was already counted when
// topped up) separated from the "what are people spending balance on"
// breakdown, which are two different questions that must never be summed.
function AdminRevenueDashboard() {
  const { data, isLoading } = useAdminRevenue();
  if (isLoading || !data) return <div className="text-center py-12 text-muted-foreground">Yuklanmoqda...</div>;
  const { real_revenue, trend_30d, spend_by_feature, kpi, ltv_note } = data;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Haqiqiy pul kirimi</p>
        <p className="text-[11px] text-muted-foreground mb-2">Faqat haqiqiy pul: muvaffaqiyatli onlayn to'lovlar va tasdiqlangan karta to'lovlari. Balansdan qilingan xaridlar ikki marta hisoblanmaydi.</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <KpiTile label="Bugun" value={sumFmt(real_revenue.today)} accent />
          <KpiTile label="Bu hafta" value={sumFmt(real_revenue.week)} />
          <KpiTile label="Bu oy" value={sumFmt(real_revenue.month)} />
          <KpiTile label="Jami" value={sumFmt(real_revenue.total)} />
        </div>
      </div>

      {trend_30d.length > 1 && (
        <div className="rounded-3xl bg-card border border-border p-4">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">30 kunlik trend</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={trend_30d}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(d) => d.slice(5)} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip formatter={(v) => sumFmt(v)} />
              <Line type="monotone" dataKey="total" stroke="#F0269D" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Asosiy ko'rsatkichlar</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <KpiTile label="O'rtacha daromad / foydalanuvchi" value={sumFmt(kpi.arpu)} sub={`${kpi.total_users} foydalanuvchi`} />
          <KpiTile label="O'rtacha daromad / to'lovchi" value={sumFmt(kpi.arppu)} sub={`${kpi.paying_users} to'lovchi`} />
          <KpiTile label="Oylik obuna daromadi" value={sumFmt(kpi.mrr)} sub="faol obunalar" />
          <KpiTile label="To'lovchilar ulushi" value={`${kpi.premium_conversion_pct}%`} />
        </div>
        {ltv_note && <p className="text-[11px] text-muted-foreground mt-2">💡 {ltv_note}</p>}
      </div>

      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Balans sarfi — bo'lim bo'yicha</p>
        <p className="text-[11px] text-muted-foreground mb-2">Bu — mahsulot ichida qayerga pul sarflanayotgani (yuqoridagi haqiqiy daromaddan farqli, chunki balansning o'zi allaqachon hisoblangan bo'lishi mumkin).</p>
        <div className="rounded-3xl bg-card border border-border divide-y divide-border">
          {spend_by_feature.length === 0 && <p className="p-4 text-sm text-muted-foreground text-center">Ma'lumot yo'q</p>}
          {spend_by_feature.map((r) => (
            <div key={r._id} className="flex items-center justify-between p-3.5">
              <span className="text-sm font-medium">{PURPOSE_UZ[r._id] || r._id}</span>
              <span className="text-sm tabular-nums"><strong>{sumFmt(r.total)}</strong> <span className="text-muted-foreground text-xs">· {r.count} ta</span></span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Gift Shop detail: the "gift_shop_deco"/"gift_shop_plan" rows in the
// Daromad tab's spend-by-feature list only give a total - this breaks it
// down into what's actually selling, and how much value is sitting unused
// in inventory (paid for, not yet given to anyone).
function AdminGiftShopDashboard() {
  const { data, isLoading } = useAdminGiftShop();
  if (isLoading || !data) return <div className="text-center py-12 text-muted-foreground">Yuklanmoqda...</div>;
  const { revenue, deco_total, plan_total, top_deco_gifts, plan_gift_breakdown, inventory_pending } = data;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Sovg'a do'koni — balans sarfi</p>
        <p className="text-[11px] text-muted-foreground mb-2">Bu ham "balans sarfi" — yuqoridagi haqiqiy daromadga qo'shilmaydi, chunki bu pul balansga qo'yilganda allaqachon hisoblangan.</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <KpiTile label="Bugun" value={sumFmt(revenue.today)} accent />
          <KpiTile label="Bu hafta" value={sumFmt(revenue.week)} />
          <KpiTile label="Bu oy" value={sumFmt(revenue.month)} />
          <KpiTile label="Jami" value={sumFmt(revenue.total)} />
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Kategoriya bo'yicha</p>
        <div className="grid grid-cols-2 gap-2.5">
          <KpiTile label="Dekorativ sovg'alar" value={sumFmt(deco_total)} />
          <KpiTile label="Obuna sovg'alari (Premium)" value={sumFmt(plan_total)} />
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Eng ko'p sotilgan dekorativ sovg'alar</p>
        <div className="rounded-3xl bg-card border border-border divide-y divide-border">
          {top_deco_gifts.length === 0 && <p className="p-4 text-sm text-muted-foreground text-center">Hali sotilmagan</p>}
          {top_deco_gifts.map((r) => (
            <div key={r._id} className="flex items-center justify-between p-3.5">
              <span className="text-sm font-medium flex items-center gap-2">{r.emoji} {r.label}</span>
              <span className="text-sm tabular-nums"><strong>{sumFmt(r.total)}</strong> <span className="text-muted-foreground text-xs">· {r.count} ta</span></span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Obuna sovg'alari — tarif bo'yicha</p>
        <div className="rounded-3xl bg-card border border-border divide-y divide-border">
          {plan_gift_breakdown.length === 0 && <p className="p-4 text-sm text-muted-foreground text-center">Hali sotilmagan</p>}
          {plan_gift_breakdown.map((r) => (
            <div key={r._id} className="flex items-center justify-between p-3.5">
              <span className="text-sm font-medium flex items-center gap-2">{r.emoji} {r.label}</span>
              <span className="text-sm tabular-nums"><strong>{sumFmt(r.total)}</strong> <span className="text-muted-foreground text-xs">· {r.count} ta</span></span>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-3xl border border-border bg-card p-4 flex items-center gap-3">
        <PackageOpen className="w-5 h-5 text-muted-foreground shrink-0" />
        <div>
          <p className="text-sm font-medium">Inventarda kutilmoqda</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {inventory_pending.count} ta sovg'a sotib olingan, hali hech kimga berilmagan — {sumFmt(inventory_pending.value)} qiymatida
          </p>
        </div>
      </div>
    </div>
  );
}

function AdminAuditLog() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useAdminAuditLog({ page, limit: 30 });
  const items = data?.items || [];
  const total = data?.total || 0;

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">Har bir admin harakati — kim, nima, qachon, kimga.</p>
      {isLoading && <div className="text-center py-8 text-muted-foreground">Yuklanmoqda...</div>}
      <div className="rounded-3xl bg-card border border-border divide-y divide-border">
        {!isLoading && items.length === 0 && <p className="p-6 text-center text-sm text-muted-foreground">Yozuvlar yo'q</p>}
        {items.map((r) => (
          <div key={r.id} className="p-3.5 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">{r.admin_name || r.admin_id}</span>
              <span className="text-[11px] text-muted-foreground tabular-nums">{new Date(r.at).toLocaleString("uz-UZ")}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              <span className="text-[11px] bg-muted rounded px-1.5 py-0.5">{actionUz(r.action)}</span>
              {r.target_name && <> → {r.target_name}</>}
              {r.details && Object.keys(r.details).length > 0 && (
                <span className="block mt-1 text-[11px] break-words">
                  {Object.entries(r.details).map(([k, v]) => `${FIELD_UZ[k] || k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`).join(" · ")}
                </span>
              )}
            </p>
          </div>
        ))}
      </div>
      <AdminPagination page={page} setPage={setPage} total={total} limit={30} />
    </div>
  );
}

// Command-center dashboard: revenue at a glance, actionable "needs attention"
// cards that jump to the relevant tab, full overview metrics, and top regions.
const StatCard = React.memo(function StatCard({ label, value, icon }) {
  return (
    <div className="rounded-3xl bg-card border border-border p-4">
      <div className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1">{icon}{label}</div>
      <p className="font-heading text-2xl mt-1">{value}</p>
    </div>
  );
});

// Sends to every onboarded, non-blocked user - both in-app (Notifications
// page) and Telegram (push_notif already forwards marketing pushes to
// Telegram, which is the channel that actually gets seen without the user
// having opened the mini app first). Dry-run first so an admin sees the
// audience size before actually sending.
function AdminBroadcast() {
  const [text, setText] = useState("");
  const [preview, setPreview] = useState(null);
  const [audience, setAudience] = useState("onboarded");
  const broadcast = useAdminBroadcast();

  const AUDIENCES = [
    ["onboarded", "Anketali a'zolar", "Onboarding'dan o'tganlar — ilova ichida + Telegram"],
    ["incomplete", "Anketasi chala", "Hisob ochgan, lekin anketani tugatmaganlar — Telegram + «Anketani tugatish» tugmasi"],
    ["bot_only", "Faqat bot (app ochmagan)", "/start bosgan, lekin ilovani umuman ochmaganlar — Telegram + «FIDEM'ni ochish» tugmasi"],
  ];

  const checkAudience = () => {
    if (!text.trim()) return;
    broadcast.mutate({ text, dryRun: true, audience }, {
      onSuccess: (data) => setPreview(data.would_send),
      onError: () => toast.error("Xatolik"),
    });
  };

  const send = () => {
    if (!text.trim()) return;
    if (!window.confirm(`${preview ?? "?"} ta foydalanuvchiga yuborilsinmi? Bu qaytarib bo'lmaydi.`)) return;
    broadcast.mutate({ text, dryRun: false, audience }, {
      onSuccess: (data) => {
        // Fanout runs in the background on the server (can take minutes at
        // scale) - the request returns as soon as it's queued, not once
        // every notification is actually sent.
        toast.success(`Navbatga qo'yildi: ${data.queued} ta foydalanuvchiga yuborilmoqda`);
        setText("");
        setPreview(null);
      },
      onError: () => toast.error("Yuborishda xatolik"),
    });
  };

  return (
    <div className="max-w-xl space-y-4">
      <div className="rounded-3xl bg-card border border-border p-5">
        <p className="text-sm font-medium mb-2">Kimga yuboriladi</p>
        <div className="space-y-1.5 mb-4">
          {AUDIENCES.map(([k, label, hint]) => (
            <button
              key={k}
              type="button"
              onClick={() => { setAudience(k); setPreview(null); }}
              className={`w-full text-left rounded-2xl border px-3 py-2.5 transition ${audience === k ? "border-primary bg-primary/5" : "border-border bg-card hover:bg-muted"}`}
            >
              <p className="text-sm font-medium">{label}</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">{hint}</p>
            </button>
          ))}
        </div>
        <p className="text-sm font-medium mb-2">Xabar matni</p>
        <textarea
          value={text}
          onChange={(e) => { setText(e.target.value); setPreview(null); }}
          rows={5}
          placeholder="Masalan: Yangi imkoniyat qo'shildi - kim profilingizni ko'rganini endi ko'ra olasiz!"
          className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm outline-none focus:border-primary resize-none"
        />
        <p className="text-xs text-muted-foreground mt-2">
          Yuqorida tanlangan segmentga yuboriladi. Avval «Auditoriyani tekshirish» bilan nechta odamga borishini ko'ring.
        </p>
        <div className="flex gap-2 mt-4">
          <button
            onClick={checkAudience}
            disabled={!text.trim() || broadcast.isPending}
            className="flex-1 rounded-2xl border border-border py-3 text-sm font-medium disabled:opacity-50"
          >
            Auditoriyani tekshirish
          </button>
          <button
            onClick={send}
            disabled={!text.trim() || preview === null || broadcast.isPending}
            className="flex-1 rounded-2xl bg-primary text-white py-3 text-sm font-medium disabled:opacity-50"
          >
            {broadcast.isPending ? "..." : "Yuborish"}
          </button>
        </div>
        {preview !== null && (
          <p className="text-xs text-secondary mt-3 text-center">{preview} ta foydalanuvchiga yuboriladi</p>
        )}
      </div>
    </div>
  );
}

// Quick audience segments: joined recently / active recently / paying.
const USER_SEGMENTS = [
  { k: "all", label: "Hammasi", params: {} },
  { k: "new", label: "🆕 Yangi (7 kun)", params: { joined_within_days: 7, sort: "new" } },
  { k: "active", label: "🟢 Faol (7 kun)", params: { active_within_days: 7, sort: "active" } },
  { k: "regular", label: "🔁 Doimiy (bugun faol)", params: { active_within_days: 1, sort: "active" } },
  { k: "paid", label: "💎 To'lovchilar", params: { plan: "paid" } },
];

function AdminUsers() {
  // Search is debounced: typing used to fire a server query on EVERY
  // keystroke, which is a big part of why the panel felt frozen.
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  React.useEffect(() => {
    const id = setTimeout(() => setQ(qInput.trim()), 350);
    return () => clearTimeout(id);
  }, [qInput]);
  const [segment, setSegment] = useState("all");
  const [filters, setFilters] = useState({ gender: "", region: "", age_min: "", age_max: "", marital_status: "" });
  const [page, setPage] = useState(1);
  const [selectedUser, setSelectedUser] = useState(null);
  const [zoomPhoto, setZoomPhoto] = useState(null);
  const limit = 20;

  const params = { q, page, limit, ...(USER_SEGMENTS.find((s) => s.k === segment)?.params || {}) };
  if (filters.gender) params.gender = filters.gender;
  if (filters.region) params.region = filters.region;
  if (filters.marital_status) params.marital_status = filters.marital_status;
  if (filters.age_min) params.age_min = parseInt(filters.age_min);
  if (filters.age_max) params.age_max = parseInt(filters.age_max);

  const { data, isLoading: loading } = useAdminUsers(params);
  const { data: regions = [] } = useAdminRegions();
  const list = data?.users || [];
  const total = data?.total || 0;
  const demoTotal = data?.demo_total || 0;
  const updateUser = useUpdateAdminUser();
  const deleteDemo = useDeleteDemoUsers();

  const patch = (id, p) => {
    updateUser.mutate({ id, patch: p }, {
      onSuccess: () => toast.success("Yangilandi ✓"),
      onError: () => toast.error("Foydalanuvchilarni yuklashda xatolik"),
    });
  };

  const removeAllDemo = () => {
    if (!window.confirm(`Barcha ${demoTotal} ta demo profilni o'chirmoqchimisiz? Bu amalni ortga qaytarib bo'lmaydi.`)) return;
    deleteDemo.mutate(undefined, {
      onSuccess: (r) => { toast.success(`${r.data.deleted} ta demo profil o'chirildi`); setSegment("all"); setPage(1); },
      onError: () => toast.error("O'chirishda xatolik"),
    });
  };
  const removeOneDemo = (id, name) => {
    if (!window.confirm(`"${name}" demo profilini o'chirmoqchimisiz?`)) return;
    deleteDemo.mutate([id], {
      onSuccess: () => { toast.success("Demo profil o'chirildi"); setSelectedUser(null); },
      onError: () => toast.error("O'chirishda xatolik"),
    });
  };

  return (
    <div className="space-y-4" data-testid="admin-users">
      {/* Search and Filters */}
      <div className="space-y-3">
        <input value={qInput} onChange={(e) => { setQInput(e.target.value); setPage(1); }} placeholder="Ism, email yoki username bo'yicha qidirish..." className="w-full rounded-2xl border border-border bg-card px-4 py-3" data-testid="admin-user-search" />
        <div className="flex flex-wrap gap-1.5">
          {USER_SEGMENTS.map((s) => (
            <button
              key={s.k}
              data-testid={`admin-user-seg-${s.k}`}
              onClick={() => { setSegment(s.k); setPage(1); }}
              className={`whitespace-nowrap text-xs rounded-full px-3 py-1.5 border ${segment === s.k ? "bg-foreground text-background border-foreground" : "bg-card border-border"}`}
            >
              {s.label}{s.k === "demo" && demoTotal > 0 ? ` (${demoTotal})` : ""}
            </button>
          ))}
        </div>
        {segment === "demo" && demoTotal > 0 && (
          <button
            data-testid="admin-delete-all-demo"
            onClick={removeAllDemo}
            disabled={deleteDemo.isPending}
            className="w-full flex items-center justify-center gap-1.5 rounded-2xl bg-rose-50 text-rose-700 border border-rose-200 px-4 py-2.5 text-sm font-medium disabled:opacity-50"
          >
            <Trash2 className="w-4 h-4" /> {deleteDemo.isPending ? "O'chirilmoqda..." : `Barcha ${demoTotal} ta demo profilni o'chirish`}
          </button>
        )}
        <details className="rounded-2xl border border-border bg-card px-4 py-3" data-testid="admin-user-filters">
          <summary className="cursor-pointer text-sm font-medium">Filtrlar</summary>
        <div className="grid grid-cols-2 gap-2 mt-3">
          <select value={filters.gender} onChange={(e) => setFilters(f => ({ ...f, gender: e.target.value }))} className="rounded-xl border border-border bg-card px-3 py-2 text-sm w-full">
            <option value="">Jins: Hammasi</option>
            <option value="male">Erkak</option>
            <option value="female">Ayol</option>
          </select>
          <select value={filters.marital_status} onChange={(e) => setFilters(f => ({ ...f, marital_status: e.target.value }))} className="rounded-xl border border-border bg-card px-3 py-2 text-sm w-full">
            <option value="">Oilaviy holat: Hammasi</option>
            <option value="single">Yolg'iz</option>
            <option value="married">Turmush qurgan</option>
            <option value="divorced">Ajrashgan</option>
            <option value="widowed">Beva</option>
          </select>
          <select value={filters.region} onChange={(e) => setFilters(f => ({ ...f, region: e.target.value }))} className="rounded-xl border border-border bg-card px-3 py-2 text-sm w-full col-span-2">
            <option value="">Hudud: Hammasi</option>
            {regions.map(r => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
          <input type="number" placeholder="Yosh (dan)" value={filters.age_min} onChange={(e) => setFilters(f => ({ ...f, age_min: e.target.value }))} className="rounded-xl border border-border bg-card px-3 py-2 text-sm w-full" />
          <input type="number" placeholder="Yosh (gacha)" value={filters.age_max} onChange={(e) => setFilters(f => ({ ...f, age_max: e.target.value }))} className="rounded-xl border border-border bg-card px-3 py-2 text-sm w-full" />
          <button onClick={() => setFilters({ gender: "", region: "", age_min: "", age_max: "", marital_status: "" })} className="col-span-2 text-xs rounded-full border border-border px-3 py-2">Tozalash</button>
        </div>
        </details>
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
                <p className="text-sm font-medium truncate flex items-center gap-1.5">
                  {u.online && <span className="w-1.5 h-1.5 rounded-full bg-secondary shrink-0" />}
                  {u.name} · {planUz(u.plan)} {u.blocked ? "🚫" : ""}
                  {u.is_demo && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 font-semibold shrink-0">DEMO</span>}
                </p>
                <p className="text-xs text-muted-foreground truncate">{u.region} · {u.age} yosh · {genderUz(u.gender)} · {maritalUz(u.marital_status)}</p>
                <p className="text-[10px] text-muted-foreground">{u.email} · {u.phone || "Telefon yo'q"}</p>
                <p className="text-[10px] text-muted-foreground">
                  {u.online ? "Hozir onlayn" : `Oxirgi faollik: ${u.last_active_label || "—"}`}
                  {u.created_at ? ` · Qo'shilgan: ${new Date(u.created_at).toLocaleDateString("uz-UZ")}` : ""}
                  {u.days_in_app != null ? ` (${u.days_in_app} kun)` : ""}
                </p>
              </div>
              <ChevronRight className="w-5 h-5 text-muted-foreground flex-shrink-0" />
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      <AdminPagination page={page} setPage={setPage} total={total} limit={limit} />

      {/* User Detail Modal */}
      {selectedUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedUser(null)}>
          <div className="bg-card rounded-3xl border border-border max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-heading text-xl font-semibold flex items-center gap-2">
                Foydalanuvchi tafsilotlari
                {selectedUser.is_demo && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 font-semibold">DEMO</span>}
              </h3>
              <button onClick={() => setSelectedUser(null)} className="p-2 rounded-full hover:bg-muted">✕</button>
            </div>

            {selectedUser.is_demo && (
              <button
                data-testid="admin-delete-one-demo"
                onClick={() => removeOneDemo(selectedUser.id, selectedUser.name)}
                disabled={deleteDemo.isPending}
                className="mb-4 w-full flex items-center justify-center gap-1.5 rounded-2xl bg-rose-50 text-rose-700 border border-rose-200 px-4 py-2.5 text-sm font-medium disabled:opacity-50"
              >
                <Trash2 className="w-4 h-4" /> Bu demo profilni o'chirish
              </button>
            )}

            <div className="space-y-4">
              {/* Profile */}
              <div className="flex items-center gap-4 p-4 bg-muted rounded-2xl">
                <div className="w-20 h-20 rounded-full bg-muted overflow-hidden cursor-pointer hover:opacity-80 transition-opacity" onClick={() => selectedUser.photo_url && setZoomPhoto(selectedUser.photo_url)}>
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
                  <p className="text-xs text-muted-foreground">IP manzil</p>
                  <p className="font-medium font-mono text-sm">{selectedUser.ip_address || "Unknown"}</p>
                </div>
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Qurilma (User Agent)</p>
                  <p className="font-medium text-xs break-all">{selectedUser.user_agent || "Unknown"}</p>
                </div>
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Oxirgi faollik</p>
                  <p className="font-medium text-sm">{selectedUser.last_active ? new Date(selectedUser.last_active).toLocaleString("uz-UZ") : "Unknown"}</p>
                </div>
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Qo'shilgan sana</p>
                  <p className="font-medium text-sm">{selectedUser.created_at ? new Date(selectedUser.created_at).toLocaleString("uz-UZ") : "Unknown"}</p>
                </div>
              </div>

              {/* Account Info */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Tarif</p>
                  <p className="font-medium">{selectedUser.plan}</p>
                </div>
                <div className="p-3 bg-muted rounded-xl">
                  <p className="text-xs text-muted-foreground">Balans</p>
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

              {/* Activity stats — loaded from the detail endpoint (matches,
                  likes, messages, reports, referrals, lifetime spend). */}
              <AdminUserActivityPanel userId={selectedUser.id} />

              {/* Actions */}
              <div className="flex gap-2 flex-wrap">
                <button onClick={() => patch(selectedUser.id, { verified_selfie: !selectedUser.verified_selfie })} className="text-xs rounded-full bg-secondary/10 text-secondary px-3 py-2">{selectedUser.verified_selfie ? "✓ Selfie tasdiqlangan" : "Selfieni tasdiqlash"}</button>
                <button onClick={() => patch(selectedUser.id, { verified_financial: !selectedUser.verified_financial })} className="text-xs rounded-full bg-gold-light text-yellow-900 px-3 py-2">{selectedUser.verified_financial ? "💎 Moliyaviy tasdiqlangan" : "Moliyaviyni tasdiqlash"}</button>
                <button onClick={() => patch(selectedUser.id, { plan: selectedUser.plan === "premium" ? "free" : "premium" })} className="text-xs rounded-full bg-primary/10 text-foreground px-3 py-2">{selectedUser.plan === "premium" ? "Premiumni olib tashlash" : "Premium berish"}</button>
                {selectedUser.plan === "vip" && (
                  <button onClick={() => patch(selectedUser.id, { plan: "premium" })} className="text-xs rounded-full bg-ink text-gold px-3 py-2">Eski VIP → Premium</button>
                )}
                <button onClick={() => patch(selectedUser.id, { add_balance: 10000 })} className="text-xs rounded-full border border-border px-3 py-2">+10k</button>
                <button onClick={() => patch(selectedUser.id, { blocked: !selectedUser.blocked })} className={`text-xs rounded-full px-3 py-2 ${selectedUser.blocked ? "bg-emerald-100 text-emerald-700" : "bg-red-50 text-red-700"}`}>{selectedUser.blocked ? "Blokdan chiqarish" : "Bloklash"}</button>
              </div>

              {/* Moderation / growth quick actions — one tap, all audit-logged */}
              <AdminUserQuickActions userId={selectedUser.id} />
            </div>
          </div>
        </div>
      )}

      {/* Photo Zoom Modal */}
      {zoomPhoto && (
        <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-[60] p-4" onClick={() => setZoomPhoto(null)}>
          <img src={photoSrc(zoomPhoto)} alt="Zoomed" className="max-w-full max-h-full object-contain" onClick={(e) => e.stopPropagation()} />
          <button onClick={() => setZoomPhoto(null)} className="absolute top-4 right-4 p-2 rounded-full bg-white/20 text-white hover:bg-white/30">✕</button>
        </div>
      )}
    </div>
  );
}

function AdminUserActivityPanel({ userId }) {
  const { data, isLoading } = useAdminUserDetail(userId);
  if (isLoading || !data) return <div className="text-xs text-muted-foreground py-2">Faollik yuklanmoqda...</div>;
  return (
    <div>
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Faollik</p>
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
        <KpiTile label="Matchlar" value={data.matches_count} />
        <KpiTile label="Like yuborgan" value={data.likes_sent} />
        <KpiTile label="Like olgan" value={data.likes_received} />
        <KpiTile label="Xabarlar" value={data.messages_sent} />
        <KpiTile label="Chatlar" value={data.chats_count} />
        <KpiTile label="Referallar" value={data.referral_count} />
        <KpiTile label="Shikoyat (unga)" value={data.reports_against_count} accent={data.reports_against_count > 0} />
        <KpiTile label="Shikoyat (undan)" value={data.reports_by_count} />
        <KpiTile label="Jami to'lagan" value={sumFmt(data.lifetime_paid_total)} sub={`${data.lifetime_paid_count} ta to'lov`} />
      </div>
      {(data.shadow_banned || data.muted) && (
        <p className="text-[11px] text-amber-600 mt-2">
          {data.shadow_banned && "🕶 Shadow-banned (feed'da ko'rinmaydi) "}
          {data.muted && "🔇 Mute (xabar yubora olmaydi)"}
        </p>
      )}
    </div>
  );
}

function AdminUserQuickActions({ userId }) {
  const { data } = useAdminUserDetail(userId);
  const actionMut = useAdminUserAction();
  const [days, setDays] = useState(30);

  const run = (action, confirmMsg) => {
    if (confirmMsg && !window.confirm(confirmMsg)) return;
    actionMut.mutate({ id: userId, action, days }, {
      onSuccess: () => toast.success("Bajarildi ✓"),
      onError: () => toast.error("Xatolik"),
    });
  };

  return (
    <div>
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Tezkor harakatlar</p>
      <div className="flex items-center gap-2 mb-2">
        <label className="text-[11px] text-muted-foreground">Tarif muddati (kun):</label>
        <input type="number" value={days} onChange={(e) => setDays(parseInt(e.target.value) || 30)} className="w-16 rounded-lg border border-border bg-background px-2 py-1 text-xs" />
      </div>
      <div className="flex gap-2 flex-wrap">
        <button onClick={() => run("give_premium")} disabled={actionMut.isPending} className="text-xs rounded-full bg-gold-light text-yellow-900 px-3 py-2 inline-flex items-center gap-1 disabled:opacity-50"><Crown className="w-3 h-3" /> Premium berish</button>
        <button onClick={() => run("reset_balance", "Balansni 0 ga tushirishga ishonchingiz komilmi?")} disabled={actionMut.isPending} className="text-xs rounded-full border border-border px-3 py-2 disabled:opacity-50">Balansni tozalash</button>
        <button onClick={() => run("reset_likes", "Barcha yoqtirishlarini o'chirishga ishonchingiz komilmi?")} disabled={actionMut.isPending} className="text-xs rounded-full border border-border px-3 py-2 disabled:opacity-50">Like'larni tozalash</button>
        <button onClick={() => run(data?.muted ? "unmute" : "mute")} disabled={actionMut.isPending} className={`text-xs rounded-full px-3 py-2 inline-flex items-center gap-1 disabled:opacity-50 ${data?.muted ? "bg-emerald-100 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
          <VolumeX className="w-3 h-3" /> {data?.muted ? "Mute'ni olish" : "Mute qilish"}
        </button>
        <button onClick={() => run(data?.shadow_banned ? "unshadow_ban" : "shadow_ban")} disabled={actionMut.isPending} className={`text-xs rounded-full px-3 py-2 inline-flex items-center gap-1 disabled:opacity-50 ${data?.shadow_banned ? "bg-emerald-100 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
          <EyeOff className="w-3 h-3" /> {data?.shadow_banned ? "Shadow ban'ni olish" : "Shadow ban"}
        </button>
        <button onClick={() => run("ban", "Bu foydalanuvchini ban qilishga ishonchingiz komilmi?")} disabled={actionMut.isPending} className="text-xs rounded-full bg-red-50 text-red-700 px-3 py-2 inline-flex items-center gap-1 disabled:opacity-50">
          <Ban className="w-3 h-3" /> Ban qilish
        </button>
        <button onClick={() => run("fraud_block", "Firibgarlik deb belgilaymizmi? Balans 0 ga qaytariladi va hisob bloklanadi, foydalanuvchiga ogohlantirish yuboriladi.")} disabled={actionMut.isPending} className="text-xs rounded-full bg-rose-100 text-rose-800 px-3 py-2 inline-flex items-center gap-1 disabled:opacity-50 font-semibold">
          <AlertTriangle className="w-3 h-3" /> Firibgarlik — balans 0 + blok
        </button>
      </div>
    </div>
  );
}

// Anonslar: create photo+text news posts; optional in-app notification fanout.
// Common in-app sections admins actually want to send people to from a post
// (e.g. "become an ambassador" -> Referral), so they don't have to remember
// or type the path.
const ANON_ACTION_PRESETS = [
  { label: "Do'stlarni taklif qilish", url: "/referral" },
  { label: "Tariflar", url: "/premium" },
  { label: "Reyting", url: "/rankings" },
];

function AnnouncementForm({ initial, busy, onCancel, onSubmit, submitLabel }) {
  const [title, setTitle] = useState(initial?.title || "");
  const [text, setText] = useState(initial?.text || "");
  const [imageUrl, setImageUrl] = useState(initial?.image_url || "");
  const [actionUrl, setActionUrl] = useState(initial?.action_url || "");
  const [actionLabel, setActionLabel] = useState(initial?.action_label || "");
  const [notify, setNotify] = useState(initial ? false : true);
  const [uploading, setUploading] = useState(false);
  const fileRef = React.useRef(null);

  const pickImage = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const up = await api.post("/files/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setImageUrl(up.data.url);
      toast.success("Rasm yuklandi ✓");
    } catch {
      toast.error("Rasm yuklashda xatolik");
    } finally { setUploading(false); }
  };

  return (
    <div className="space-y-3">
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Sarlavha" className="w-full rounded-2xl border border-border bg-background px-4 py-2.5 text-sm" data-testid="anons-title" />
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={4} placeholder="Matn (ixtiyoriy)" className="w-full rounded-2xl border border-border bg-background px-4 py-2.5 text-sm" data-testid="anons-text" />
      <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={pickImage} />
      <div className="flex items-center gap-2 flex-wrap">
        <button type="button" onClick={() => fileRef.current?.click()} disabled={uploading} className="text-xs rounded-full border border-border px-3 py-2 disabled:opacity-50">
          {imageUrl ? "Rasmni almashtirish" : "📷 Rasm biriktirish"}
        </button>
        {imageUrl && <img src={photoSrc(imageUrl)} alt="" className="h-10 w-16 object-cover rounded-lg border border-border" />}
      </div>

      <div className="rounded-2xl border border-dashed border-border p-3 space-y-2">
        <p className="text-xs font-medium text-muted-foreground flex items-center gap-1.5"><Link2 className="w-3.5 h-3.5" /> Tugma / havola (ixtiyoriy)</p>
        <p className="text-[11px] text-muted-foreground">Post oxirida tugma chiqadi va bosilganda shu bo'limga yoki havolaga o'tkazadi (masalan Instagram post, yoki ilova ichidagi bo'lim).</p>
        <div className="flex gap-2 flex-wrap">
          {ANON_ACTION_PRESETS.map((p) => (
            <button key={p.url} type="button" onClick={() => { setActionUrl(p.url); setActionLabel((v) => v || p.label); }}
              className="text-[11px] rounded-full border border-border px-2.5 py-1 hover:bg-muted">
              {p.label}
            </button>
          ))}
        </div>
        <input value={actionUrl} onChange={(e) => setActionUrl(e.target.value)} placeholder="/referral yoki https://instagram.com/..." className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm" data-testid="anons-action-url" />
        <input value={actionLabel} onChange={(e) => setActionLabel(e.target.value)} placeholder="Tugma matni (masalan: Do'stlarni taklif qilish)" className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm" data-testid="anons-action-label" />
      </div>

      {!initial && (
        <label className="flex items-center gap-1.5 text-xs">
          <input type="checkbox" checked={notify} onChange={(e) => setNotify(e.target.checked)} />
          Bildirishnoma yuborilsin (ilova ichida + Telegram bot)
        </label>
      )}

      <div className="flex gap-2">
        {onCancel && (
          <button type="button" onClick={onCancel} disabled={busy} className="flex-1 rounded-2xl border border-border text-sm font-medium py-2.5">
            Bekor qilish
          </button>
        )}
        <button
          type="button"
          onClick={() => onSubmit({ title: title.trim(), text: text.trim(), image_url: imageUrl || null, action_url: actionUrl.trim() || null, action_label: actionLabel.trim() || null, notify })}
          disabled={busy || !title.trim() || uploading}
          data-testid="anons-publish"
          className="flex-1 rounded-2xl bg-primary text-white text-sm font-medium py-2.5 disabled:opacity-50"
        >
          {busy ? "..." : submitLabel}
        </button>
      </div>
    </div>
  );
}

function AdminAnnouncements() {
  const queryClient = useQueryClient();
  const { data: items = [] } = useAdminAnnouncements();
  const [busy, setBusy] = useState(false);
  const [editingId, setEditingId] = useState(null);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["admin", "announcements"] });
    queryClient.invalidateQueries({ queryKey: ["announcements"] });
  };

  const publish = async (payload) => {
    setBusy(true);
    try {
      await api.post("/admin/announcements", payload);
      toast.success("Anons e'lon qilindi ✓");
      invalidate();
    } catch {
      toast.error("Xatolik");
    } finally { setBusy(false); }
  };

  const saveEdit = async (id, payload) => {
    setBusy(true);
    try {
      await api.patch(`/admin/announcements/${id}`, {
        title: payload.title, text: payload.text,
        image_url: payload.image_url, clear_image: !payload.image_url,
        action_url: payload.action_url, action_label: payload.action_label,
        clear_action: !payload.action_url,
      });
      toast.success("Yangilandi ✓");
      setEditingId(null);
      invalidate();
    } catch {
      toast.error("Xatolik");
    } finally { setBusy(false); }
  };

  const remove = async (id) => {
    try {
      await api.delete(`/admin/announcements/${id}`);
      toast.success("O'chirildi");
      invalidate();
    } catch { toast.error("Xatolik"); }
  };

  return (
    <div className="space-y-4 max-w-2xl" data-testid="admin-anons">
      <div className="rounded-3xl bg-card border border-border p-4">
        <p className="text-sm font-medium mb-3">Yangi anons</p>
        <AnnouncementForm busy={busy} onSubmit={publish} submitLabel="E'lon qilish" />
      </div>

      <div className="space-y-2">
        {items.map((a) => (
          <div key={a.id} className="rounded-2xl bg-card border border-border p-3" data-testid={`adm-anons-${a.id}`}>
            {editingId === a.id ? (
              <AnnouncementForm
                initial={a}
                busy={busy}
                onCancel={() => setEditingId(null)}
                onSubmit={(payload) => saveEdit(a.id, payload)}
                submitLabel="Saqlash"
              />
            ) : (
              <div className="flex items-center gap-3">
                {a.image_url && <img src={photoSrc(a.image_url)} alt="" className="h-12 w-16 object-cover rounded-lg border border-border shrink-0" />}
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate">{a.title}</p>
                  <div className="flex items-center gap-2.5 text-[10px] text-muted-foreground mt-0.5">
                    <span>{a.created_at ? new Date(a.created_at).toLocaleString("uz-UZ") : ""}</span>
                    <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {a.view_count || 0} kishi ko'rdi</span>
                    {a.action_url && <span className="flex items-center gap-1 text-primary"><Link2 className="w-3 h-3" /> {a.action_label || a.action_url}</span>}
                  </div>
                </div>
                <button onClick={() => setEditingId(a.id)} className="shrink-0 p-2 rounded-full hover:bg-muted text-muted-foreground" title="Tahrirlash">
                  <Pencil className="w-4 h-4" />
                </button>
                <button onClick={() => remove(a.id)} className="shrink-0 p-2 rounded-full hover:bg-muted text-rose-600" title="O'chirish">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// Launch promo switch: Premium free for every woman while it is on.
function AdminWomenFreePromo() {
  const [promo, setPromo] = useState(null);
  const [saving, setSaving] = useState(false);
  React.useEffect(() => { api.get("/admin/promo").then((r) => setPromo(r.data)).catch(() => {}); }, []);
  const toggle = async () => {
    if (!promo || saving) return;
    const next = !promo.women_free;
    if (!window.confirm(next ? "Ayollar uchun Premium bepul qilinsinmi?" : "Ayollar uchun bepul Premium o'chirilsinmi? Ular yana oddiy tarifga qaytadi.")) return;
    setSaving(true);
    try {
      await api.post("/admin/promo", { women_free: next });
      setPromo({ ...promo, women_free: next });
      toast.success("Saqlandi");
    } catch { toast.error("Xatolik"); } finally { setSaving(false); }
  };
  return (
    <div className="rounded-3xl bg-card border border-border p-5 flex items-center justify-between gap-3" data-testid="admin-women-free">
      <div>
        <p className="text-sm font-semibold">🎁 Ayollar uchun Premium bepul</p>
        <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
          Yoqilganda har bir ayol Premium'ning barcha imkoniyatlaridan bepul foydalanadi.
          {promo ? ` Hozir ${promo.women_count} ta ayol anketasi.` : ""}
        </p>
      </div>
      <button onClick={toggle} disabled={!promo || saving} data-testid="admin-women-free-toggle"
        className={`shrink-0 w-12 h-7 rounded-full transition relative ${promo?.women_free ? "bg-secondary" : "bg-muted"}`}>
        <span className={`absolute top-1 w-5 h-5 rounded-full bg-white shadow transition-all ${promo?.women_free ? "left-6" : "left-1"}`} />
      </button>
    </div>
  );
}

function AdminManualTopups() {
  const { data: health } = useAdminConfigHealth();
  // Temporary P2P top-up moderation while CLICK is down: admin publishes a
  // card number, users transfer + attach a receipt, admin credits balances.
  const [cfg, setCfg] = useState(null);
  const [saving, setSaving] = useState(false);
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("pending");
  const [busy, setBusy] = useState(null);

  const loadItems = React.useCallback((s) => {
    api.get(`/admin/manual-topups?status=${s}&limit=50`).then((r) => setItems(r.data.items || [])).catch(() => {});
  }, []);
  React.useEffect(() => {
    api.get("/admin/topup-config").then((r) => setCfg(r.data)).catch(() => {});
  }, []);
  React.useEffect(() => { loadItems(status); }, [status, loadItems]);

  const saveCfg = async () => {
    setSaving(true);
    try {
      await api.post("/admin/topup-config", {
        p2p_enabled: !!cfg.p2p_enabled,
        card_number: cfg.card_number || "",
        card_holder: cfg.card_holder || "",
      });
      toast.success("Saqlandi");
    } catch (e) {
      toast.error((e?.response?.data?.detail || "Xatolik").toString());
    } finally { setSaving(false); }
  };

  const decide = async (id, approve) => {
    let reason = "";
    if (!approve) {
      reason = window.prompt("Rad etish sababi (foydalanuvchiga ko'rinadi):") || "";
      if (!reason.trim()) return;
    } else if (!window.confirm("Pul kartaga KELGANINI bank ilovangizda tekshirdingizmi? Tasdiq balansga darhol tushiradi.")) {
      return;
    }
    setBusy(id);
    try {
      await api.post(`/admin/manual-topups/${id}/decide`, { approve, reason });
      toast.success(approve ? "Tasdiqlandi — balans tushdi" : "Rad etildi");
      loadItems(status);
    } catch {
      toast.error("Xatolik");
    } finally { setBusy(null); }
  };

  // Reversal for an approved P2P request that turns out to be fraudulent
  // (money never actually landed - only checkable in the real bank app) -
  // zeroes the balance it credited, blocks the account, and warns the user
  // in one call instead of chaining 3 separate admin actions.
  const flagFraud = async (row) => {
    if (!window.confirm(`"${row.user?.name || row.user_id}" hisobini firibgarlik deb belgilaymizmi? Balans 0 ga qaytariladi va hisob bloklanadi.`)) return;
    setBusy(row.id);
    try {
      await api.post(`/admin/users/${row.user_id}/action`, { action: "fraud_block" });
      toast.success("Balans 0 ga qaytarildi, hisob bloklandi");
      loadItems(status);
    } catch {
      toast.error("Xatolik");
    } finally { setBusy(null); }
  };

  const hamyonOn = !!health?.hamyon_configured;
  return (
    <div className="max-w-2xl space-y-4">
      <AdminWomenFreePromo />
      {hamyonOn && (
        <div className="rounded-3xl border border-emerald-200 bg-emerald-50 dark:bg-emerald-950/30 p-5" data-testid="admin-hamyon-on">
          <p className="text-sm font-semibold text-emerald-900 dark:text-emerald-200">✓ Hamyon ulangan — to'lovlar avtomatik tasdiqlanadi</p>
          <p className="text-xs text-emerald-800 dark:text-emerald-300 mt-1.5 leading-relaxed">
            Foydalanuvchi kartaga aniq summani o'tkazadi, Hamyon pulni ko'rgach tarif yoki balans o'zi yoqiladi.
            Hammasi «To'lovlar» bo'limida ko'rinadi. Qo'lda chek tekshirish kerak emas.
          </p>
        </div>
      )}
      {!hamyonOn && (
      <>
      {/* Config: toggle + receiving card */}
      <div className="rounded-3xl bg-card border border-border p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold">Karta orqali to'ldirish rejimi</p>
            <p className="text-xs text-muted-foreground mt-0.5">Yoqilsa — foydalanuvchilar ko'rsatilgan kartaga pul o'tkazib, chek yuboradi; siz tasdiqlaganingizdan keyin balansiga tushadi. Yoqilishi bilan ilovadagi "To'lov tez orada" holati o'chadi va Premium sotuvi ochiladi.</p>
          </div>
          <button
            onClick={() => setCfg((c) => ({ ...(c || {}), p2p_enabled: !c?.p2p_enabled }))}
            className={`shrink-0 w-12 h-7 rounded-full transition relative ${cfg?.p2p_enabled ? "bg-secondary" : "bg-muted"}`}
            data-testid="p2p-toggle"
          >
            <span className={`absolute top-0.5 w-6 h-6 rounded-full bg-white shadow transition-all ${cfg?.p2p_enabled ? "left-[22px]" : "left-0.5"}`} />
          </button>
        </div>
        <input
          value={cfg?.card_number || ""}
          onChange={(e) => setCfg((c) => ({ ...(c || {}), card_number: e.target.value.replace(/\D/g, "").slice(0, 16) }))}
          placeholder="Karta raqami (16 raqam)"
          inputMode="numeric"
          className="w-full rounded-2xl border border-border bg-background px-4 py-2.5 text-sm tabular-nums outline-none focus:border-primary"
        />
        <input
          value={cfg?.card_holder || ""}
          onChange={(e) => setCfg((c) => ({ ...(c || {}), card_holder: e.target.value }))}
          placeholder="Karta egasi (masalan: AZIZ V.)"
          className="w-full rounded-2xl border border-border bg-background px-4 py-2.5 text-sm outline-none focus:border-primary"
        />
        <button onClick={saveCfg} disabled={saving || !cfg} className="rounded-2xl bg-primary text-white text-sm font-medium px-5 py-2.5 disabled:opacity-50">
          {saving ? "..." : "Saqlash"}
        </button>
      </div>
      </>
      )}

      {/* Queue (old manual card top-ups; hidden once Hamyon is on and nothing is waiting) */}
      {(!hamyonOn || items.length > 0 || status !== "pending") && (
      <>
      <div className="flex gap-2">
        {[["pending", "Kutilmoqda"], ["approved", "Tasdiqlangan"], ["rejected", "Rad etilgan"]].map(([k, l]) => (
          <button key={k} onClick={() => setStatus(k)}
            className={`px-4 py-2 rounded-full text-xs font-medium ${status === k ? "bg-primary text-white" : "bg-muted/40 text-muted-foreground"}`}>
            {l}
          </button>
        ))}
      </div>
      <div className="space-y-2">
        {items.length === 0 && <p className="text-sm text-muted-foreground py-6 text-center">So'rovlar yo'q</p>}
        {items.map((r) => (
          <div key={r.id} className="rounded-2xl bg-card border border-border p-4 flex items-center gap-3 flex-wrap">
            <div className="flex-1 min-w-[160px]">
              <p className="text-sm font-medium flex items-center gap-1.5">
                {r.user?.name || r.user_id} · <span className="tabular-nums font-semibold">{Number(r.amount).toLocaleString()} so'm</span>
                {r.decided_by === "ai" && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-violet-100 text-violet-700 font-semibold shrink-0">🤖 AI</span>}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">{new Date(r.created_at).toLocaleString()} · balans: {Number(r.user?.balance || 0).toLocaleString()}</p>
              {r.rejection_reason && <p className="text-xs text-primary mt-0.5">{r.rejection_reason}</p>}
              {r.ai_review?.ai_generated && (
                <p className="text-[11px] text-violet-700 mt-1 bg-violet-50 rounded-lg px-2 py-1">
                  🤖 {r.ai_review.verdict} ({r.ai_review.confidence}%) — {r.ai_review.reason || "—"}
                </p>
              )}
            </div>
            <a href={photoSrc(r.proof_url)} target="_blank" rel="noreferrer" className="text-xs text-secondary underline shrink-0">Chekni ko'rish</a>
            {r.status === "pending" && (
              <div className="flex gap-2 shrink-0">
                <button onClick={() => decide(r.id, true)} disabled={busy === r.id}
                  className="rounded-full bg-secondary text-white text-xs font-semibold px-4 py-2 disabled:opacity-50">Tasdiqlash</button>
                <button onClick={() => decide(r.id, false)} disabled={busy === r.id}
                  className="rounded-full border border-border text-xs font-semibold px-4 py-2 disabled:opacity-50">Rad etish</button>
              </div>
            )}
            {r.status === "approved" && (
              <button onClick={() => flagFraud(r)} disabled={busy === r.id}
                className="shrink-0 rounded-full border border-rose-300 text-rose-700 text-xs font-semibold px-4 py-2 disabled:opacity-50">
                Firibgarlik — bloklash
              </button>
            )}
          </div>
        ))}
      </div>
      </>
      )}
    </div>
  );
}

const METHOD_UZ = { hamyon: "Karta (Hamyon)", balance: "Balansdan", manual_p2p: "Karta (qo'lda)", click: "CLICK" };

function AdminPayments() {
  // Successful payments are the default view; pending/expired/failed noise
  // is collapsed behind a toggle. Every row names the paying user.
  const [showOther, setShowOther] = useState(false);
  const [page, setPage] = useState(1);
  const limit = 20;
  const { data } = useAdminPayments({ page, limit, status: showOther ? "other" : "successful" });
  const list = data?.payments || [];
  const total = data?.total || 0;
  const blockMutation = useAdminPaymentBlock();

  const blockPayment = (id) => blockMutation.mutate({ id, block: true }, { onSuccess: () => toast.success("Bloklandi") });
  const unblockPayment = (id) => blockMutation.mutate({ id, block: false }, { onSuccess: () => toast.success("Blokdan chiqarildi") });

  const statusPill = (s, method) => {
    if (s === "success" || s === "paid") return <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-medium">✓ {METHOD_UZ[method] || (s === "paid" ? "Balansdan" : "Onlayn")}</span>;
    if (s === "pending") return <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">Kutilmoqda</span>;
    return <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-100 text-rose-700">{s}</span>;
  };

  return (
    <div className="space-y-3" data-testid="admin-payments">
      <div className="flex gap-1.5">
        <button
          onClick={() => { setShowOther(false); setPage(1); }}
          className={`text-xs rounded-full px-3 py-1.5 border ${!showOther ? "bg-foreground text-background border-foreground" : "bg-card border-border"}`}
          data-testid="adm-pay-tab-success"
        >
          ✓ Muvaffaqiyatli
        </button>
        <button
          onClick={() => { setShowOther(true); setPage(1); }}
          className={`text-xs rounded-full px-3 py-1.5 border ${showOther ? "bg-foreground text-background border-foreground" : "bg-card border-border"}`}
          data-testid="adm-pay-tab-other"
        >
          Jarayonda / muvaffaqiyatsiz
        </button>
      </div>
      {list.length === 0 && <p className="text-sm text-muted-foreground py-6 text-center">To'lovlar yo'q</p>}
      <div className="space-y-2">
        {list.map((p) => (
          <div key={p.id} className="rounded-2xl bg-card border border-border p-3" data-testid={`adm-pay-${p.id}`}>
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">
                  {p.user_name || p.user_id?.slice(0, 8)}
                  {p.user_telegram ? <span className="text-muted-foreground font-normal"> · @{p.user_telegram}</span> : null}
                </p>
                <p className="text-sm">{PURPOSE_UZ[p.purpose] || p.purpose}{p.days ? ` (${p.days === 30 ? "1 oy" : `${p.days} kun`})` : ""} · <span className="font-semibold tabular-nums">{p.amount?.toLocaleString()} so'm</span>{p.balance_used > 0 && p.click_amount > 0 ? <span className="text-[10px] text-muted-foreground"> (balans {p.balance_used?.toLocaleString()} + karta {(p.hamyon_amount || p.click_amount)?.toLocaleString()})</span> : null}</p>
                <p className="text-[10px] text-muted-foreground">{p.created_at ? new Date(p.created_at).toLocaleString("uz-UZ") : "—"} {p.blocked_by_admin && "· 🚫 Bloklangan"}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {statusPill(p.status, p.method)}
                {/* Blocking only means something for a payment that is still open. */}
                {p.blocked_by_admin ? (
                  <button onClick={() => unblockPayment(p.id)} className="text-xs rounded-full bg-emerald-100 text-emerald-700 px-3 py-1.5">Blokdan chiqarish</button>
                ) : ["pending", "prepared"].includes(p.status) ? (
                  <button onClick={() => blockPayment(p.id)} className="text-xs rounded-full bg-red-50 text-red-700 px-3 py-1.5">Bloklash</button>
                ) : null}
              </div>
            </div>
          </div>
        ))}
      </div>
      <AdminPagination page={page} setPage={setPage} total={total} limit={limit} />
    </div>
  );
}

function AdminVerifications() {
  // Full evidence view: WHO is asking, WHAT they submitted (proof photo,
  // tappable to zoom) and the AI reviewer's verdict. Confident AI verdicts
  // are auto-applied server-side - this queue holds only the unclear ones.
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("pending");
  const [zoom, setZoom] = useState(null);
  const limit = 20;
  const { data } = useAdminVerifications({ page, limit, status });
  const list = data?.verifications || [];
  const total = data?.total || 0;
  const decideMutation = useAdminDecideVerification();
  const decide = (id, approve) => {
    const reason = approve ? "" : (prompt("Rad etish sababi:") || "");
    decideMutation.mutate({ id, approve, reason }, {
      onSuccess: () => toast.success(approve ? "Tasdiqlandi ✓" : "Rad etildi"),
      onError: () => toast.error("Xatolik"),
    });
  };

  const aiBadge = (v) => {
    if (!v.ai_verdict) return <span className="text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground inline-flex items-center gap-1"><Bot className="w-3 h-3" /> AI: tekshirilmagan</span>;
    if (v.ai_verdict === "approve") return <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 inline-flex items-center gap-1"><Bot className="w-3 h-3" /> AI: tasdiqlagan ({v.ai_confidence}%)</span>;
    if (v.ai_verdict === "reject") return <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-100 text-rose-700 inline-flex items-center gap-1"><Bot className="w-3 h-3" /> AI: rad etgan ({v.ai_confidence}%)</span>;
    return <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 inline-flex items-center gap-1"><Bot className="w-3 h-3" /> AI: ishonchsiz — o'zingiz ko'ring</span>;
  };

  return (
    <div className="space-y-3" data-testid="admin-verifs">
      <div className="flex gap-1.5">
        {[["pending", "Kutilmoqda"], ["all", "Barchasi"]].map(([k, label]) => (
          <button key={k} onClick={() => { setStatus(k); setPage(1); }} className={`text-xs rounded-full px-3 py-1.5 border ${status === k ? "bg-foreground text-background border-foreground" : "bg-card border-border"}`}>{label}</button>
        ))}
      </div>
      {list.length === 0 && <p className="text-sm text-muted-foreground py-6 text-center">Kutilayotganlar yo'q</p>}
      {list.map((v) => (
        <div key={v.id} className="rounded-2xl bg-card border border-border p-3" data-testid={`adm-verif-${v.id}`}>
          <div className="flex items-start gap-3">
            {v.proof_url ? (
              <img
                src={photoSrc(v.proof_url)}
                alt=""
                onClick={() => setZoom(v.proof_url)}
                className="w-20 h-20 object-cover rounded-xl border border-border cursor-zoom-in shrink-0"
                data-testid={`adm-verif-proof-${v.id}`}
              />
            ) : (
              <div className="w-20 h-20 rounded-xl bg-muted grid place-items-center text-[10px] text-muted-foreground shrink-0">Dalil yo'q</div>
            )}
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">
                {VERIF_KIND_UZ[v.kind] || v.kind}
                <span className="text-muted-foreground font-normal"> · {v.user?.name || v.user_id?.slice(0, 8)}</span>
                {v.status !== "pending" && (
                  <span className={`ml-1.5 text-[10px] px-1.5 py-0.5 rounded-full ${v.status === "approved" ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"}`}>
                    {v.status === "approved" ? "Tasdiqlangan" : "Rad etilgan"}{v.decided_by === "ai" ? " (AI)" : ""}
                  </span>
                )}
              </p>
              {v.note && <p className="text-xs text-muted-foreground mt-0.5">{v.note}</p>}
              <div className="mt-1.5">{aiBadge(v)}</div>
              {v.ai_reason && <p className="text-[11px] text-muted-foreground mt-1 leading-snug">{v.ai_reason}</p>}
            </div>
            {v.status === "pending" && (
              <div className="flex flex-col gap-1.5 shrink-0">
                <button data-testid={`adm-verif-yes-${v.id}`} onClick={() => decide(v.id, true)} className="text-xs rounded-full bg-secondary text-white px-4 py-1.5">✓ Tasdiqlash</button>
                <button data-testid={`adm-verif-no-${v.id}`} onClick={() => decide(v.id, false)} className="text-xs rounded-full border border-border px-4 py-1.5">✕ Rad etish</button>
              </div>
            )}
          </div>
        </div>
      ))}
      <AdminPagination page={page} setPage={setPage} total={total} limit={limit} />
      {zoom && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={() => setZoom(null)}>
          <img src={photoSrc(zoom)} alt="" className="max-w-full max-h-full rounded-2xl" />
        </div>
      )}
    </div>
  );
}

function AdminReports() {
  const { data: list = [] } = useAdminReports();
  return (
    <div className="space-y-2" data-testid="admin-reports">
      {list.length === 0 && <p className="text-sm text-muted-foreground">Shikoyatlar yo'q</p>}
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
  const [filter, setFilter] = useState("pending");
  const [page, setPage] = useState(1);
  const [selectedWithdrawal, setSelectedWithdrawal] = useState(null);
  const limit = 20;
  const { data } = useAdminWithdrawals({ status: filter || undefined, page, limit });
  const list = data?.withdrawals || [];
  const total = data?.total || 0;
  const decisionMutation = useAdminWithdrawalDecision();

  const approve = (id) => decisionMutation.mutate({ id, approve: true }, { onSuccess: () => toast.success("Tasdiqlandi") });
  const reject = (id) => {
    const reason = prompt("Rad etish sababi:") || "";
    decisionMutation.mutate({ id, approve: false, reason }, { onSuccess: () => toast.success("Rad etildi") });
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
                <p className="text-[10px] text-muted-foreground">{new Date(w.created_at).toLocaleString("uz-UZ")} · {statusUz(w.status)}</p>
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
      <AdminPagination page={page} setPage={setPage} total={total} limit={limit} />

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
                  <p className="font-medium">{statusUz(selectedWithdrawal.status)}</p>
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

function AdminConciergeAnalyticsPanel() {
  const { data, isLoading } = useAdminConciergeAnalytics();
  if (isLoading || !data) return null;
  return (
    <div className="rounded-3xl bg-card border border-border p-4">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Buyurtmalar statistikasi</p>
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
        <KpiTile label="Arizalar" value={data.applications} />
        <KpiTile label="To'lov kutmoqda" value={data.awaiting_payment} />
        <KpiTile label="Jarayonda" value={data.in_progress} />
        <KpiTile label="Yakunlangan" value={data.completed} />
        <KpiTile label="Daromad" value={sumFmt(data.revenue_generated)} accent />
        <KpiTile label="Konversiya" value={`${data.conversion_pct}%`} />
      </div>
    </div>
  );
}

function AdminConcierge() {
  const [search, setSearch] = useState("");
  const { data: list = [] } = useAdminConcierge();
  const { data: userSearchData } = useAdminUserSearch(search);
  const users = userSearchData?.users || [];
  const matchMutation = useAdminConciergeMatch();

  const addMatch = (orderId, matchUserId) => {
    const note = prompt("Mos haqida izoh (ixtiyoriy):") || "";
    matchMutation.mutate({ orderId, matchUserId, note }, {
      onSuccess: () => toast.success("Mos qo'shildi"),
      onError: () => toast.error("Xato"),
    });
  };

  return (
    <div className="space-y-3" data-testid="admin-concierge">
      <AdminConciergeAnalyticsPanel />
      <input placeholder="Foydalanuvchi qidirish (mos qo'shish uchun)..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full rounded-2xl border border-border bg-card px-4 py-3 text-sm" />
      {list.length === 0 && <p className="text-sm text-muted-foreground">Buyurtma yo'q</p>}
      {list.map((o) => (
        <div key={o.id} className="rounded-2xl bg-card border border-border p-3" data-testid={`adm-con-${o.id}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">{o.user?.name || o.user_id?.slice(0, 8)} · {(o.amount || 0).toLocaleString()} so'm</p>
              <p className="text-xs text-muted-foreground">Holat: {statusUz(o.status)} · {(o.matches || []).length}/5 nomzod</p>
            </div>
            <span className={`text-[10px] px-2 py-1 rounded-full ${o.status === "in_progress" ? "bg-amber-100 text-amber-700" : o.status === "completed" ? "bg-emerald-100 text-emerald-700" : "bg-muted text-muted-foreground"}`}>{statusUz(o.status)}</span>
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
  // Referrer-centric view: WHO is distributing links, how many they brought
  // in, and per-invitee paid/free status. The raw earnings ledger stays
  // available behind a toggle.
  const [openId, setOpenId] = useState(null);
  const [showLedger, setShowLedger] = useState(false);
  const { data: referrers = [], isLoading } = useAdminReferrers();
  const { data: detail } = useAdminReferrerDetail(openId);
  const { data: ledger = [] } = useAdminReferrals({});
  const [summary, setSummary] = useState(null);
  React.useEffect(() => { api.get("/admin/referrals/summary").then((r) => setSummary(r.data)).catch(() => {}); }, []);

  return (
    <div className="space-y-3" data-testid="admin-referrals">
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2" data-testid="admin-ref-summary">
          <KpiTile label="Taklif bilan kelgan" value={summary.invited} />
          <KpiTile label="To'lov qilgan" value={summary.paid} sub={`${summary.conversion_pct}%`} />
          <KpiTile label="Kutilayotgan mukofot" value={sumFmt(summary.earnings_pending)} sub="14 kunlik tekshiruvda" />
          <KpiTile label="Yechishga tayyor" value={sumFmt(summary.earnings_withdrawable)} sub={summary.pending_withdrawals ? `${summary.pending_withdrawals} ta so'rov kutmoqda` : "so'rov yo'q"} accent={summary.pending_withdrawals > 0} />
        </div>
      )}
      {isLoading && <p className="text-sm text-muted-foreground py-4 text-center">Yuklanmoqda...</p>}
      {!isLoading && referrers.length === 0 && (
        <p className="text-sm text-muted-foreground py-6 text-center">Hozircha hech kim referal orqali odam taklif qilmagan</p>
      )}

      {referrers.map((r) => {
        const rid = r.referrer?.id;
        const isOpen = openId === rid;
        return (
          <div key={r.code} className="rounded-2xl bg-card border border-border" data-testid={`adm-referrer-${r.code}`}>
            <button
              className="w-full text-left p-3 flex items-center justify-between gap-2"
              onClick={() => setOpenId(isOpen ? null : rid)}
              disabled={!rid}
            >
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">
                  {r.referrer?.name}
                  {r.referrer?.telegram_username ? <span className="text-muted-foreground font-normal"> · @{r.referrer.telegram_username}</span> : null}
                  {r.referrer?.plan && r.referrer.plan !== "free" ? <span className="text-[10px] ml-1 px-1.5 py-0.5 rounded-full bg-gold/15 text-gold-dark uppercase">{r.referrer.plan}</span> : null}
                </p>
                <p className="text-xs text-muted-foreground">
                  Taklif qilgan: <strong className="text-foreground">{r.invited}</strong> · To'lovga o'tgan: <strong className="text-foreground">{r.paid}</strong>
                  {r.referrer?.earnings_pending > 0 && ` · Hold: ${r.referrer.earnings_pending.toLocaleString()} so'm`}
                  {r.referrer?.earnings_withdrawable > 0 && ` · Yechishga tayyor: ${r.referrer.earnings_withdrawable.toLocaleString()} so'm`}
                </p>
              </div>
              <ChevronRight className={`w-4 h-4 text-muted-foreground shrink-0 transition-transform ${isOpen ? "rotate-90" : ""}`} />
            </button>

            {isOpen && detail && (
              <div className="border-t border-border/60 p-3 space-y-1.5" data-testid="adm-referrer-detail">
                <p className="text-[11px] text-muted-foreground">
                  Jami {detail.invited_total} ta taklif · {detail.invited_paid} tasi pullik tarifda
                </p>
                {detail.invited.map((u) => (
                  <div key={u.id} className="flex items-center justify-between gap-2 py-1.5 border-b border-border/40 last:border-0">
                    <div className="min-w-0">
                      <p className="text-xs font-medium truncate">{u.name || u.id.slice(0, 8)} <span className="text-muted-foreground font-normal">· {u.region || "—"}</span></p>
                      <p className="text-[10px] text-muted-foreground">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString("uz-UZ") : "—"}
                        {u.onboarded ? " · anketa to'liq" : " · anketa chala"}
                      </p>
                    </div>
                    {u.is_paid ? (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-medium shrink-0">💎 {u.plan}</span>
                    ) : (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground shrink-0">free</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}

      <button
        onClick={() => setShowLedger((v) => !v)}
        className="text-xs text-muted-foreground underline"
        data-testid="adm-ref-ledger-toggle"
      >
        {showLedger ? "Daromad yozuvlarini yashirish" : "Daromad yozuvlarini ko'rsatish"}
      </button>
      {showLedger && ledger.map((r) => (
        <div key={r.id} className="rounded-2xl bg-card border border-border p-3" data-testid={`adm-ref-${r.id}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">{REF_TYPE_UZ[r.type] || r.type} · <span className="text-foreground">{r.amount?.toLocaleString()} so'm</span></p>
              <p className="text-xs text-muted-foreground">{r.user_id?.slice(0, 8)} → {r.referred_user_id?.slice(0, 8)}</p>
              <p className="text-[10px] text-muted-foreground">{new Date(r.created_at).toLocaleString("uz-UZ")} · {statusUz(r.status)}</p>
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

function AdminChatModAnalyticsPanel({ onOpenUser }) {
  const { data, isLoading } = useAdminChatModAnalytics();
  if (isLoading || !data) return null;
  return (
    <div className="rounded-3xl bg-card border border-border p-4 space-y-3">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Chat Analitika</p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <KpiTile label="Bloklangan juftlar" value={data.blocked_relationships} />
        <KpiTile label="Ochiq shikoyatlar" value={data.reports_open} accent={data.reports_open > 0} />
        <KpiTile label="Jami shikoyatlar" value={data.reports_total} />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <p className="text-[11px] text-muted-foreground mb-1.5">Eng faol foydalanuvchilar (hafta)</p>
          <div className="space-y-1">
            {data.most_active_users.slice(0, 5).map((r) => (
              <button key={r._id} onClick={() => onOpenUser(r._id)} className="w-full flex items-center justify-between text-xs rounded-lg hover:bg-muted px-2 py-1.5">
                <span className="truncate">{r.user?.name || r._id}</span>
                <span className="text-muted-foreground tabular-nums">{r.n} xabar</span>
              </button>
            ))}
            {data.most_active_users.length === 0 && <p className="text-xs text-muted-foreground px-2">Ma'lumot yo'q</p>}
          </div>
        </div>
        <div>
          <p className="text-[11px] text-muted-foreground mb-1.5">Eng ko'p shikoyat qilinganlar</p>
          <div className="space-y-1">
            {data.most_reported_users.slice(0, 5).map((r) => (
              <button key={r._id} onClick={() => onOpenUser(r._id)} className="w-full flex items-center justify-between text-xs rounded-lg hover:bg-muted px-2 py-1.5">
                <span className="truncate">{r.user?.name || r._id}</span>
                <span className="text-red-600 tabular-nums">{r.n} shikoyat</span>
              </button>
            ))}
            {data.most_reported_users.length === 0 && <p className="text-xs text-muted-foreground px-2">Ma'lumot yo'q</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

function AdminMessages() {
  const [q, setQ] = useState("");
  const [userIdFilter, setUserIdFilter] = useState("");
  const [page, setPage] = useState(1);
  const limit = 20;
  const params = { q, page, limit };
  if (userIdFilter) params.user_id = userIdFilter;
  const { data, isLoading: loading } = useAdminMessages(params);
  const list = data?.messages || [];
  const total = data?.total || 0;
  const deleteMutation = useAdminDeleteMessage();

  const deleteMsg = (id) => {
    if (confirm("Xabarni o'chirmoqchimisiz?")) {
      deleteMutation.mutate(id, { onSuccess: () => toast.success("O'chirildi") });
    }
  };

  return (
    <div className="space-y-4" data-testid="admin-messages">
      <AdminChatModAnalyticsPanel onOpenUser={setUserIdFilter} />
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
      <AdminPagination page={page} setPage={setPage} total={total} limit={limit} />
    </div>
  );
}

function AdminFraud() {
  const [page, setPage] = useState(1);
  const [minScore, setMinScore] = useState(50);
  const limit = 50;
  const { data } = useAdminFraud({ min_score: minScore, page, limit });
  const list = data?.users || [];
  const total = data?.total || 0;
  const markSafeMutation = useAdminMarkSafe();

  const markSafe = (uid) => markSafeMutation.mutate(uid, { onSuccess: () => toast.success("Xavfsiz deb belgilandi") });

  return (
    <div className="space-y-4" data-testid="admin-fraud">
      <div className="flex gap-2 items-center">
        <label className="text-sm">Minimal fraud ball:</label>
        <input type="number" value={minScore} onChange={(e) => { setMinScore(Number(e.target.value)); setPage(1); }} className="rounded-xl border border-border bg-card px-3 py-2 text-sm w-24" />
      </div>
      {list.length === 0 && <p className="text-sm text-muted-foreground">Shubhali foydalanuvchilar topilmadi</p>}
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
                  <p className="text-xs text-muted-foreground">{u.email} · {u.ip_address || "IP noma'lum"}</p>
                  {u.fraud_reasons && u.fraud_reasons.length > 0 && (
                    <p className="text-[10px] text-red-600">{u.fraud_reasons.join(", ")}</p>
                  )}
                </div>
              </div>
              <div className="flex gap-1">
                {u.flagged_as_bot && <span className="text-[10px] px-2 py-1 rounded-full bg-red-100 text-red-700">🤖 Bot</span>}
                <button onClick={() => markSafe(u.id)} className="text-xs rounded-full bg-emerald-100 text-emerald-700 px-2 py-1">Xavfsiz</button>
              </div>
            </div>
          </div>
        ))}
      </div>
      <AdminPagination page={page} setPage={setPage} total={total} limit={limit} />
    </div>
  );
}
