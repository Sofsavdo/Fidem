import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { Lock } from "lucide-react";

const TABS = [
  { k: "mine", api: "/saved/mine", labelKey: "saved_by_me" },
  { k: "by_others", api: "/saved/by-others", labelKey: "saved_me" },
  { k: "viewers", api: "/saved/viewers", labelKey: "viewed_my_profile" },
  { k: "interested", api: "/saved/interested", labelKey: "interested_in_me" },
];

export default function Saved() {
  const { t, user } = useApp();
  const [tab, setTab] = useState("mine");
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const cur = TABS.find((x) => x.k === tab);
    setLoading(true);
    api.get(cur.api).then((r) => setData((d) => ({ ...d, [tab]: r.data || [] }))).finally(() => setLoading(false));
  }, [tab]);

  const items = data[tab] || [];

  return (
    <div className="px-4 pt-6">
      <h1 className="font-heading text-3xl font-semibold tracking-tight mb-4">{t("saved")}</h1>
      <div className="flex gap-1 mb-4 overflow-x-auto no-scrollbar -mx-4 px-4">
        {TABS.map((x) => (
          <button
            key={x.k}
            data-testid={`saved-tab-${x.k}`}
            onClick={() => setTab(x.k)}
            className={`whitespace-nowrap rounded-full px-3 py-1.5 text-xs border transition ${
              tab === x.k ? "bg-foreground text-background border-foreground" : "bg-card border-border"
            }`}
          >
            {t(x.labelKey)}
          </button>
        ))}
      </div>

      {loading && <div className="text-center py-6 text-muted-foreground">{t("loading")}</div>}
      {!loading && items.length === 0 && <div className="text-center py-12 text-muted-foreground" data-testid="saved-empty">{t("no_data")}</div>}

      <div className="grid grid-cols-2 gap-3 stagger" data-testid="saved-grid">
        {items.map((c) => (
          c.locked ? (
            <div key={Math.random()} className="aspect-[4/5] rounded-3xl bg-card border border-border overflow-hidden relative">
              <div className="absolute inset-0 bg-gradient-to-b from-muted to-card flex flex-col items-center justify-center text-center p-4">
                <Lock className="w-6 h-6 text-muted-foreground" />
                <p className="text-xs text-muted-foreground mt-2">{t("premium_only")}</p>
                <Link data-testid="locked-upgrade" to="/premium" className="mt-3 text-xs font-medium text-primary underline">{t("upgrade")}</Link>
              </div>
            </div>
          ) : (
            <Link
              key={c.id}
              to={`/candidate/${c.id}`}
              data-testid={`saved-card-${c.id}`}
              className="block aspect-[4/5] rounded-3xl bg-card border border-border overflow-hidden relative hover:shadow-elevated transition-shadow"
            >
              <img
                src={c.photo_url || "https://images.unsplash.com/photo-1502685104226-ee32379fefbe?w=800"}
                alt=""
                className="w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/0 to-black/0" />
              <div className="absolute bottom-2 left-3 right-3 text-white">
                <p className="font-medium text-sm">{c.name}, {c.age}</p>
                <p className="text-[10px] text-white/85">{c.region}</p>
              </div>
            </Link>
          )
        ))}
      </div>
    </div>
  );
}
