// Product-focus switches. The app's core loop is: verified profile -> daily
// candidates -> mutual interest -> chat -> contact exchange. Anything that
// pulls attention away from it (leaderboards, gift shop, paid boosts, the
// extra Standard/VIP tiers) is OFF by default; flip a flag at build time with
// REACT_APP_FEATURE_<NAME>=1 to bring one back. Routes stay mounted so old
// deep links and notifications still resolve.
const flag = (name) => {
  const v = process.env[`REACT_APP_FEATURE_${name}`];
  return v === "1" || v === "true";
};

export const FEATURES = {
  rankings: flag("RANKINGS"),       // gift leaderboard + "boost your rank"
  giftShop: flag("GIFT_SHOP"),      // standalone gift shop entry
  boost: flag("BOOST"),             // paid profile boost
  legacyTiers: flag("LEGACY_TIERS"), // sell Standard / VIP besides Premium
};
