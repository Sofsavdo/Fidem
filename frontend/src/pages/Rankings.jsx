import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, Trophy, Users, MapPin, Calendar, Crown, Medal, Award } from "lucide-react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";

export default function Rankings() {
  const { t } = useApp();
  const [activeTab, setActiveTab] = useState("global");
  const [rankings, setRankings] = useState([]);
  const [myRankings, setMyRankings] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadRankings = async (tab) => {
    setLoading(true);
    try {
      let endpoint = "/rankings/global";
      if (tab === "men") endpoint = "/rankings/men";
      else if (tab === "women") endpoint = "/rankings/women";
      else if (tab === "ambassadors") endpoint = "/rankings/ambassadors";
      
      const r = await api.get(endpoint);
      setRankings(r.data.rankings || []);
    } catch {/* ignore */}
    finally { setLoading(false); }
  };

  const loadMyRankings = async () => {
    try {
      const r = await api.get("/rankings/me");
      setMyRankings(r.data.my_rankings);
    } catch {/* ignore */}
  };

  useEffect(() => { loadMyRankings(); }, []);
  useEffect(() => { loadRankings(activeTab); }, [activeTab]);

  const tabs = [
    { id: "global", label: "Global", icon: Trophy },
    { id: "men", label: "Men", icon: Users },
    { id: "women", label: "Women", icon: Users },
    { id: "ambassadors", label: "Ambassadors", icon: Crown },
  ];

  const getRankBadge = (rank) => {
    if (rank === 1) return <Medal className="w-5 h-5 text-yellow-500" />;
    if (rank === 2) return <Medal className="w-5 h-5 text-gray-400" />;
    if (rank === 3) return <Medal className="w-5 h-5 text-amber-700" />;
    return <span className="text-sm font-medium text-muted-foreground">#{rank}</span>;
  };

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <Link to="/me" className="p-2 -ml-2 rounded-full hover:bg-muted">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <span className="font-heading font-bold text-lg">Rankings</span>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* Tabs */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap ${
                activeTab === tab.id
                  ? "bg-primary text-white"
                  : "bg-muted/30 text-muted-foreground"
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* My Rankings */}
        {myRankings && (
          <section className="rounded-3xl border border-border bg-gradient-to-br from-primary/10 to-secondary/10 p-4">
            <h3 className="font-heading font-semibold mb-3 flex items-center gap-2">
              <Award className="w-5 h-5" /> Your Rank
            </h3>
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-xl bg-card p-3">
                <p className="text-xs text-muted-foreground">Global</p>
                <p className="text-lg font-heading font-bold">#{myRankings.global?.rank || "—"}</p>
              </div>
              <div className="rounded-xl bg-card p-3">
                <p className="text-xs text-muted-foreground">Score</p>
                <p className="text-lg font-heading font-bold">{myRankings.global?.ranking_score || 0}</p>
              </div>
            </div>
          </section>
        )}

        {/* Rankings List */}
        <section className="rounded-3xl border border-border bg-card p-6">
          <h2 className="font-heading font-semibold mb-4 capitalize">{activeTab} Rankings</h2>
          
          {loading ? (
            <div className="text-center text-sm text-muted-foreground py-8">{t("loading")}</div>
          ) : rankings.length === 0 ? (
            <div className="text-center text-sm text-muted-foreground py-8">No rankings yet</div>
          ) : (
            <div className="space-y-3">
              {rankings.map((user) => (
                <div
                  key={user.user_id}
                  className={`flex items-center gap-3 p-3 rounded-xl ${
                    user.rank <= 3 ? "bg-gradient-to-r from-gold/10 to-transparent" : "bg-muted/30"
                  }`}
                >
                  <div className="w-10 flex justify-center">
                    {getRankBadge(user.rank)}
                  </div>
                  {user.photo_url ? (
                    <img
                      src={user.photo_url}
                      alt={user.name}
                      className="w-10 h-10 rounded-full object-cover"
                    />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center">
                      <Users className="w-5 h-5 text-muted-foreground" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{user.name}</p>
                    <p className="text-xs text-muted-foreground">{user.city}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold">{user.ranking_score}</p>
                    <p className="text-[11px] text-muted-foreground capitalize">{user.status}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Info */}
        <div className="rounded-2xl border border-border bg-card p-4 flex gap-3 text-sm">
          <Calendar className="w-4 h-4 text-primary shrink-0 mt-0.5" />
          <div className="text-muted-foreground">
            <p>Rankings are updated daily based on influence score, activity, and contribution.</p>
          </div>
        </div>
      </main>
    </div>
  );
}
