// Small UI helpers
import { API } from "@/lib/api";

// Derive from the API constant (env with a hardcoded fallback) — reading
// REACT_APP_BACKEND_URL directly returns undefined in a misconfigured build,
// which made the prefix check below never match and served photos without
// the auth token (401 on every image).
const BACKEND = API.replace(/\/api$/, "");

/** Return a usable image URL. If url is hosted on our backend's /api/files/ endpoint,
 *  append the current viewer's JWT as ?auth= so <img> tags can authenticate. */
export function photoSrc(url) {
  if (!url) return null;
  // Photos are stored with whatever backend host served the app when they were
  // uploaded; after a domain change that host is dead although the file is
  // still ours. Always resolve our own files against the CURRENT backend.
  const at = url.indexOf("/api/files/");
  if (at >= 0) {
    const absolute = `${BACKEND}${url.slice(at)}`;
    const token = localStorage.getItem("fidem_token");
    if (!token) return absolute;
    const sep = absolute.includes("?") ? "&" : "?";
    return `${absolute}${sep}auth=${token}`;
  }
  return url;
}
