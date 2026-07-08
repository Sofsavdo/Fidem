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
