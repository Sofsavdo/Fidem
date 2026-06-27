// Small UI helpers
const BACKEND = process.env.REACT_APP_BACKEND_URL;

/** Return a usable image URL. If url is hosted on our backend's /api/files/ endpoint,
 *  append the current viewer's JWT as ?auth= so <img> tags can authenticate. */
export function photoSrc(url) {
  if (!url) return null;
  const filesPrefix = `${BACKEND}/api/files/`;
  if (url.startsWith(filesPrefix) || url.startsWith("/api/files/")) {
    const absolute = url.startsWith("http") ? url : `${BACKEND}${url}`;
    const token = localStorage.getItem("fidem_token");
    if (!token) return absolute;
    const sep = absolute.includes("?") ? "&" : "?";
    return `${absolute}${sep}auth=${token}`;
  }
  return url;
}
