import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export const QK = {
  referral: ["referral", "mine"],
  referralUsername: ["referral", "username"],
  notifications: ["notifications"],
  dailyStatus: ["daily", "status"],
  rankings: (tab) => ["rankings", tab],
  myRankings: ["rankings", "me"],
  candidates: (filters) => ["candidates", filters],
  candidateDetail: (id) => ["candidates", "detail", id],
  saved: (tab = "mine") => ["saved", tab],
  withdrawalsStatus: ["withdrawals", "status"],
  withdrawalsHistory: ["withdrawals", "history"],
  payments: ["payments", "mine"],
  giftsCatalog: ["gifts", "catalog"],
  conciergeInfo: ["concierge", "info"],
  conciergeMine: ["concierge", "mine"],
  personalityQuestions: (lang) => ["personality", "questions", lang],
  personalityMine: ["personality", "mine"],
  familyContact: ["family", "contact", "mine"],
  familyRequests: ["family", "mine"],
  promptsLibrary: (lang) => ["prompts", "library", lang],
  promptsMine: ["prompts", "mine"],
  stories: ["stories"],
  verificationMine: ["verification", "mine"],
  messagesChats: ["messages", "chats"],
  messagesApplications: ["messages", "applications"],
  adminStats: ["admin", "stats"],
  adminUsers: (params) => ["admin", "users", params],
  adminRegions: ["admin", "regions"],
  adminUserSearch: (q) => ["admin", "userSearch", q],
  adminPayments: (params) => ["admin", "payments", params],
  adminVerifications: (params) => ["admin", "verifications", params],
  adminReports: ["admin", "reports"],
  adminWithdrawals: (params) => ["admin", "withdrawals", params],
  adminConcierge: ["admin", "concierge"],
  adminReferrals: (params) => ["admin", "referrals", params],
  adminMessages: (params) => ["admin", "messages", params],
  adminFraud: (params) => ["admin", "fraud", params],
};

export function useReferral() {
  return useQuery({
    queryKey: QK.referral,
    queryFn: () => api.get("/referral/mine").then((r) => r.data),
  });
}

export function useReferralUsername() {
  return useQuery({
    queryKey: QK.referralUsername,
    queryFn: () => api.get("/referral/username/status").then((r) => r.data),
  });
}

export function useNotifications() {
  return useQuery({
    queryKey: QK.notifications,
    queryFn: () => api.get("/notifications").then((r) => r.data || []),
    staleTime: 30_000,
  });
}

export function useDailyStatus() {
  return useQuery({
    queryKey: QK.dailyStatus,
    queryFn: () => api.get("/daily/status").then((r) => r.data),
  });
}

const RANKINGS_ENDPOINTS = {
  men: "/rankings/men",
  women: "/rankings/women",
  ambassadors: "/rankings/ambassadors",
};

export function useRankings(tab = "global") {
  const endpoint = RANKINGS_ENDPOINTS[tab] || "/rankings/global";
  return useQuery({
    queryKey: QK.rankings(tab),
    queryFn: () => api.get(endpoint).then((r) => r.data?.rankings || []),
  });
}

export function useMyRankings() {
  return useQuery({
    queryKey: QK.myRankings,
    queryFn: () => api.get("/rankings/me").then((r) => r.data?.my_rankings || null),
  });
}

export function useCandidates(filters = {}) {
  return useQuery({
    queryKey: QK.candidates(filters),
    queryFn: () => api.get("/candidates", { params: filters }).then((r) => r.data || []),
  });
}

export function useCandidateDetail(id) {
  return useQuery({
    queryKey: QK.candidateDetail(id),
    queryFn: () => api.get(`/candidates/${id}`).then((r) => r.data),
    enabled: !!id,
  });
}

export function useSaved(tab = "mine") {
  const endpoint = tab === "mine" ? "/saved/mine" : `/saved/${tab === "by_others" ? "by-others" : tab}`;
  return useQuery({
    queryKey: QK.saved(tab),
    queryFn: () => api.get(endpoint).then((r) => r.data || []),
  });
}

export function useWithdrawalsStatus() {
  return useQuery({
    queryKey: QK.withdrawalsStatus,
    queryFn: () => api.get("/withdrawals/status").then((r) => r.data),
  });
}

export function useWithdrawalsHistory() {
  return useQuery({
    queryKey: QK.withdrawalsHistory,
    queryFn: () => api.get("/withdrawals/mine").then((r) => r.data || []),
  });
}

export function usePayments() {
  return useQuery({
    queryKey: QK.payments,
    queryFn: () => api.get("/payments/mine").then((r) => r.data || []),
  });
}

export function useGiftsCatalog() {
  return useQuery({
    queryKey: QK.giftsCatalog,
    queryFn: () => api.get("/gifts/catalog").then((r) => r.data),
    staleTime: 10 * 60 * 1000, // catalog changes rarely
  });
}

export function useConciergeInfo() {
  return useQuery({
    queryKey: QK.conciergeInfo,
    queryFn: () => api.get("/concierge/info").then((r) => r.data),
  });
}

export function useConciergeMine() {
  return useQuery({
    queryKey: QK.conciergeMine,
    queryFn: () => api.get("/concierge/mine").then((r) => r.data || []),
  });
}

export function usePersonalityQuestions(lang) {
  return useQuery({
    queryKey: QK.personalityQuestions(lang),
    queryFn: () => api.get(`/personality/questions?lang=${lang}`).then((r) => r.data),
    staleTime: 10 * 60 * 1000,
  });
}

export function usePersonalityMine() {
  return useQuery({
    queryKey: QK.personalityMine,
    queryFn: () => api.get("/personality/mine").then((r) => r.data),
  });
}

export function useFamilyContact() {
  return useQuery({
    queryKey: QK.familyContact,
    queryFn: () => api.get("/family/contacts/mine").then((r) => r.data),
  });
}

export function useFamilyRequests() {
  return useQuery({
    queryKey: QK.familyRequests,
    queryFn: () => api.get("/family/mine").then((r) => r.data || { sent: [], received: [] }),
  });
}

export function usePromptsLibrary(lang) {
  return useQuery({
    queryKey: QK.promptsLibrary(lang || "uz"),
    queryFn: () => api.get(`/prompts/library?lang=${lang || "uz"}`).then((r) => r.data || []),
    staleTime: 10 * 60 * 1000,
  });
}

export function usePromptsMine() {
  return useQuery({
    queryKey: QK.promptsMine,
    queryFn: () => api.get("/prompts/mine").then((r) => r.data || []),
  });
}

export function useStories() {
  return useQuery({
    queryKey: QK.stories,
    queryFn: () => api.get("/stories?limit=50").then((r) => r.data || []),
  });
}

export function useVerificationMine() {
  return useQuery({
    queryKey: QK.verificationMine,
    queryFn: () => api.get("/verification/mine").then((r) => r.data),
  });
}

export function useMessagesChats() {
  return useQuery({
    queryKey: QK.messagesChats,
    queryFn: () => api.get("/messages/chats").then((r) => r.data || []),
  });
}

export function useMessagesApplications() {
  return useQuery({
    queryKey: QK.messagesApplications,
    queryFn: () => api.get("/messages/applications").then((r) => r.data || []),
  });
}

export function useToggleSave() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, isSaved }) =>
      isSaved ? api.delete(`/saved/${id}`) : api.post("/saved", { user_id: id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.saved("mine") });
    },
  });
}

// ---------- Admin ----------
export function useAdminStats() {
  return useQuery({
    queryKey: QK.adminStats,
    queryFn: () => api.get("/admin/stats").then((r) => r.data),
  });
}

export function useAdminUsers(params) {
  return useQuery({
    queryKey: QK.adminUsers(params),
    queryFn: () => api.get("/admin/users", { params }).then((r) => r.data),
  });
}

export function useAdminRegions() {
  return useQuery({
    queryKey: QK.adminRegions,
    queryFn: () => api.get("/admin/regions").then((r) => r.data?.regions || []),
    staleTime: 10 * 60 * 1000,
  });
}

export function useAdminUserSearch(q) {
  return useQuery({
    queryKey: QK.adminUserSearch(q),
    queryFn: () => api.get("/admin/users", { params: { q } }).then((r) => r.data),
    enabled: (q || "").length >= 2,
  });
}

export function useUpdateAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }) => api.patch(`/admin/users/${id}`, patch),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "fraud"] });
    },
  });
}

export function useAdminPayments(params) {
  return useQuery({
    queryKey: QK.adminPayments(params),
    queryFn: () => api.get("/admin/payments", { params }).then((r) => r.data),
  });
}

export function useAdminPaymentBlock() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, block }) => api.post(`/admin/payments/${id}/${block ? "block" : "unblock"}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "payments"] }),
  });
}

export function useAdminVerifications(params) {
  return useQuery({
    queryKey: QK.adminVerifications(params),
    queryFn: () => api.get("/admin/verifications", { params }).then((r) => r.data),
  });
}

export function useAdminDecideVerification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, approve }) => api.post(`/admin/verifications/${id}/decide`, { approve }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "verifications"] }),
  });
}

export function useAdminReports() {
  return useQuery({
    queryKey: QK.adminReports,
    queryFn: () => api.get("/admin/reports").then((r) => r.data || []),
  });
}

export function useAdminWithdrawals(params) {
  return useQuery({
    queryKey: QK.adminWithdrawals(params),
    queryFn: () => api.get("/admin/withdrawals", { params }).then((r) => r.data),
  });
}

export function useAdminWithdrawalDecision() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, approve, reason }) =>
      approve
        ? api.post(`/admin/withdrawals/${id}/approve`)
        : api.post(`/admin/withdrawals/${id}/reject`, { reason }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "withdrawals"] }),
  });
}

export function useAdminConcierge() {
  return useQuery({
    queryKey: QK.adminConcierge,
    queryFn: () => api.get("/admin/concierge").then((r) => r.data || []),
  });
}

export function useAdminConciergeMatch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ orderId, matchUserId, note }) =>
      api.post(`/admin/concierge/${orderId}/match`, { match_user_id: matchUserId, note }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: QK.adminConcierge }),
  });
}

export function useAdminReferrals(params) {
  return useQuery({
    queryKey: QK.adminReferrals(params),
    queryFn: () => api.get("/admin/referrals", { params }).then((r) => r.data || []),
  });
}

export function useAdminMessages(params) {
  return useQuery({
    queryKey: QK.adminMessages(params),
    queryFn: () => api.get("/admin/messages", { params }).then((r) => r.data),
  });
}

export function useAdminDeleteMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => api.delete(`/admin/messages/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "messages"] }),
  });
}

export function useAdminFraud(params) {
  return useQuery({
    queryKey: QK.adminFraud(params),
    queryFn: () => api.get("/admin/fraud", { params }).then((r) => r.data),
  });
}

export function useAdminMarkSafe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (uid) => api.post(`/admin/users/${uid}/mark-safe`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "fraud"] }),
  });
}
