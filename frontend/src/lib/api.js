import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const client = axios.create({ baseURL: API });

const cache = new Map();
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

const perfLog = process.env.NODE_ENV === 'development' ? {
  requests: {},
  log: (url, duration, size, cached) => {
    if (!perfLog.requests[url]) perfLog.requests[url] = { count: 0, totalTime: 0, maxSize: 0, cached: 0 };
    perfLog.requests[url].count++;
    perfLog.requests[url].totalTime += duration;
    perfLog.requests[url].maxSize = Math.max(perfLog.requests[url].maxSize, size);
    if (cached) perfLog.requests[url].cached++;
    console.log(`[API] ${url} - ${duration}ms - ${size} bytes${cached ? ' (cached)' : ''}`);
  },
  summary: () => {
    console.log('[API Summary]', perfLog.requests);
    Object.entries(perfLog.requests).forEach(([url, stats]) => {
      const avg = Math.round(stats.totalTime / stats.count);
      console.log(`  ${url}: ${stats.count} calls, avg ${avg}ms, max ${stats.maxSize} bytes, ${stats.cached} cached`);
    });
  }
} : null;

const cacheableUrls = ['/icebreakers', '/gifts/catalog', '/me/progress'];

client.interceptors.request.use((config) => {
  config.metadata = { startTime: performance.now() };
  const token = localStorage.getItem("fidem_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  
  // Check cache for GET requests to cacheable endpoints
  if (config.method === 'get' && cacheableUrls.some(u => config.url.includes(u))) {
    const cacheKey = `${config.url}_${JSON.stringify(config.params || {})}`;
    const cached = cache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
      config.metadata.cached = true;
      config.metadata.cachedData = cached.data;
    }
  }
  
  return config;
});

client.interceptors.response.use(
  (r) => {
    const duration = performance.now() - r.config.metadata.startTime;
    const size = JSON.stringify(r.data).length;
    const cached = r.config.metadata.cached;
    
    if (cached) {
      r.data = r.config.metadata.cachedData;
    } else if (r.config.method === 'get' && cacheableUrls.some(u => r.config.url.includes(u))) {
      const cacheKey = `${r.config.url}_${JSON.stringify(r.config.params || {})}`;
      cache.set(cacheKey, { data: r.data, timestamp: Date.now() });
    }
    
    if (perfLog) perfLog.log(r.config.url, Math.round(duration), size, cached);
    return r;
  },
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("fidem_token");
      if (!window.location.pathname.startsWith("/auth")) {
        window.location.href = "/auth";
      }
    }
    return Promise.reject(err);
  }
);

if (perfLog) window.__apiPerfLog = perfLog;

export default client;
