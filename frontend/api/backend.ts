// Frontend API layer
// All fetch calls to backend are defined here.
// Page and chart components import from this file rather than calling fetch() directly.
// Endpoints are defined in backend at ingest.py and trends.py.

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

/* ---------------- helpers ---------------- */

/** Shared fetch wrapper: throws on non-ok, always logs failures. */
async function apiFetch(url: string, options?: RequestInit): Promise<any> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const msg = `[API] ${options?.method ?? "GET"} ${url} → ${res.status} ${res.statusText}`;
    console.error(msg);
    throw new Error(msg);
  }
  return res.json();
}

/* ---------------- ingest ---------------- */

export async function getRoot() {
  return apiFetch(`${API_BASE}/`);
}

export async function ingestVideos(payload: any) {
  return apiFetch(`${API_BASE}/ingest/videos`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function ingestComments(payload: any) {
  return apiFetch(`${API_BASE}/ingest/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function ingestTranscripts(payload: any) {
  return apiFetch(`${API_BASE}/ingest/transcripts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/* ---------------- videos ---------------- */

export async function getVideos(params?: { limit?: number; league?: string; channel_id?: string }) {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  if (params?.league) searchParams.set("league", params.league);
  if (params?.channel_id) searchParams.set("channel_id", params.channel_id);

  const data = await apiFetch(`${API_BASE}/ingest/videos?${searchParams.toString()}`);
  return { videos: data.videos || data.data || [] };
}

export async function getVideosByLeague(limitPerLeague?: number) {
  const searchParams = new URLSearchParams();
  if (limitPerLeague) searchParams.set("limit_per_league", limitPerLeague.toString());
  return apiFetch(`${API_BASE}/ingest/videos/by-league?${searchParams.toString()}`);
}

export async function getVideoById(videoId: string) {
  return apiFetch(`${API_BASE}/ingest/videos/${videoId}`);
}

export async function getComments(params?: { video_id?: string; limit?: number }) {
  const searchParams = new URLSearchParams();
  if (params?.video_id) searchParams.set("video_id", params.video_id);
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  return apiFetch(`${API_BASE}/ingest/comments?${searchParams.toString()}`);
}

export async function getTranscripts(videoId: string) {
  return apiFetch(`${API_BASE}/ingest/transcripts?video_id=${encodeURIComponent(videoId)}`);
}

/* ---------------- trends ---------------- */

export async function getTrends(params?: { time_window?: string; limit?: number }) {
  const searchParams = new URLSearchParams();
  if (params?.time_window) searchParams.set("time_window", params.time_window);
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  return apiFetch(`${API_BASE}/trends?${searchParams.toString()}`);
}

export async function calculateTrends(time_window_days?: number) {
  const searchParams = new URLSearchParams();
  if (time_window_days !== undefined) {
    searchParams.set("time_window_days", String(Math.round(time_window_days)));
  }

  return apiFetch(`${API_BASE}/trends/calculate?${searchParams.toString()}`, { method: "POST" });
}

export async function getNarratives() {
  return apiFetch(`${API_BASE}/trends/narratives`);
}

export async function getClaims(params?: { narrative_id?: string; limit?: number }) {
  const searchParams = new URLSearchParams();
  if (params?.narrative_id) searchParams.set("narrative_id", params.narrative_id);
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  return apiFetch(`${API_BASE}/trends/claims?${searchParams.toString()}`);
}

/* ---------------- dashboard ---------------- */

export async function getDashboardKPIs() {
  const data = await apiFetch(`${API_BASE}/ingest/dashboard/kpis`);
  return {
    videos_analyzed:        data.videos_analyzed        ?? data.total_videos   ?? 0,
    trending_topics:        data.trending_topics        ?? data.total_trends   ?? 0,
    avg_sentiment:          data.avg_sentiment          ?? 0,
    channels_tracked:       data.channels_tracked       ?? data.total_channels ?? 0,
    videos_this_week:       data.videos_this_week       ?? 0,
    topics_since_yesterday: data.topics_since_yesterday ?? 0,
    trending_claims:        data.trending_claims        ?? 0,
  };
}

export async function getLeagueStats() {
  const data = await apiFetch(`${API_BASE}/ingest/dashboard/leagues`);
  return { leagues: data.leagues || data.data || [] };
}

export async function getSentimentHistory() {
  return apiFetch(`${API_BASE}/ingest/dashboard/sentiment-history`);
}

export async function getTrendsHistory() {
  return apiFetch(`${API_BASE}/ingest/trends/history`);
}

export async function getDashboardClaims(limit?: number, daysBack?: number) {
  const searchParams = new URLSearchParams();
  if (limit) searchParams.set("limit", limit.toString());
  if (daysBack) searchParams.set("days_back", daysBack.toString());

  return apiFetch(`${API_BASE}/ingest/dashboard/claims?${searchParams.toString()}`);
}

/* ---------------- channels ---------------- */

export async function getChannels() {
  return apiFetch(`${API_BASE}/ingest/channels`);
}

export async function getChannelLatestVideo(channelId: string) {
  return apiFetch(`${API_BASE}/ingest/channels/${channelId}/latest-video`);
}

export async function getChannelRisk(channelId: string) {
  return apiFetch(`${API_BASE}/ingest/channels/${channelId}/risk`);
}

export async function getChannelsWithRisk(params?: {
  risk_level?: string;
  min_risk_score?: number;
  max_risk_score?: number;
  limit?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params?.risk_level)                                searchParams.set("risk_level",      params.risk_level);
  if (params?.min_risk_score !== undefined)              searchParams.set("min_risk_score",   params.min_risk_score.toString());
  if (params?.max_risk_score !== undefined)              searchParams.set("max_risk_score",   params.max_risk_score.toString());
  if (params?.limit)                                     searchParams.set("limit",            params.limit.toString());

  return apiFetch(`${API_BASE}/ingest/channels/risk?${searchParams.toString()}`);
}

export async function getVideosWithRisk(params?: {
  channel_id?: string;
  min_risk_score?: number;
  limit?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params?.channel_id)                   searchParams.set("channel_id",     params.channel_id);
  if (params?.min_risk_score !== undefined) searchParams.set("min_risk_score", params.min_risk_score.toString());
  if (params?.limit)                        searchParams.set("limit",          params.limit.toString());

  return apiFetch(`${API_BASE}/ingest/videos/risk?${searchParams.toString()}`);
}

/* ---------------- events ---------------- */

// NOTE: events endpoint may not exist on all environments — treated as non-fatal.
export async function getEvents(limit?: number) {
  const searchParams = new URLSearchParams();
  if (limit) searchParams.set("limit", limit.toString());

  const url = `${API_BASE}/ingest/events?${searchParams.toString()}`;
  const res = await fetch(url);

  if (!res.ok) {
    // Non-fatal: log but don't throw so callers can decide how to handle absence of events
    console.warn(`[API] GET ${url} → ${res.status} ${res.statusText} (events endpoint may be unavailable)`);
    return { events: [] };
  }

  const data = await res.json();
  return { events: data.events || data.data || [] };
}
