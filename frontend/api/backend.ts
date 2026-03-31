const API_BASE = "http://127.0.0.1:8000";

export async function getRoot() {
  const res = await fetch(`${API_BASE}/`);
  if (!res.ok) throw new Error("Failed to fetch root");
  return res.json();
}

export async function ingestVideos(payload: any) {
  const res = await fetch(`${API_BASE}/ingest/videos`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error("Failed to ingest videos");
  }

  return res.json();
}

export async function ingestComments(payload: any) {
  const res = await fetch(`${API_BASE}/ingest/comments`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error("Failed to ingest comments");
  }

  return res.json();
}

export async function ingestTranscripts(payload: any) {
  const res = await fetch(`${API_BASE}/ingest/transcripts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error("Failed to ingest transcripts");
  }

  return res.json();
}

// ============== GET Endpoints ==============

export async function getVideos(params?: { limit?: number; league?: string; channel_id?: string }) {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  if (params?.league) searchParams.set("league", params.league);
  if (params?.channel_id) searchParams.set("channel_id", params.channel_id);

  const res = await fetch(`${API_BASE}/ingest/videos?${searchParams.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch videos");
  const data = await res.json();
  return {
    videos: data.videos || data.data || [],
  };
}

export async function getVideoById(videoId: string) {
  const res = await fetch(`${API_BASE}/ingest/videos/${videoId}`);
  if (!res.ok) throw new Error("Failed to fetch video");
  return res.json();
}

export async function getComments(params?: { video_id?: string; limit?: number }) {
  const searchParams = new URLSearchParams();
  if (params?.video_id) searchParams.set("video_id", params.video_id);
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  const res = await fetch(`${API_BASE}/ingest/comments?${searchParams.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch comments");
  return res.json();
}

export async function getTranscripts(videoId: string) {
  const res = await fetch(`${API_BASE}/ingest/transcripts?video_id=${encodeURIComponent(videoId)}`);
  if (!res.ok) throw new Error("Failed to fetch transcripts");
  return res.json();
}

// ============== Trends Endpoints ==============

export async function getTrends(time_window?: string) {
  const searchParams = new URLSearchParams();
  if (time_window) searchParams.set("time_window", time_window);

  const res = await fetch(`${API_BASE}/trends?${searchParams.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch trends");
  return res.json();
}

export async function calculateTrends(time_window_days?: number) {
  const searchParams = new URLSearchParams();
  if (time_window_days !== undefined) {
    searchParams.set("time_window_days", String(Math.round(time_window_days)));
  }

  const res = await fetch(`${API_BASE}/trends/calculate?${searchParams.toString()}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to calculate trends");
  return res.json();
}

export async function getNarratives() {
  const res = await fetch(`${API_BASE}/trends/narratives`);
  if (!res.ok) throw new Error("Failed to fetch narratives");
  return res.json();
}

export async function getClaims(params?: { narrative_id?: string; limit?: number }) {
  const searchParams = new URLSearchParams();
  if (params?.narrative_id) searchParams.set("narrative_id", params.narrative_id);
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  const res = await fetch(`${API_BASE}/trends/claims?${searchParams.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch claims");
  return res.json();
}

// ============== Dashboard Endpoints ==============

export async function getDashboardKPIs() {
  const res = await fetch(`${API_BASE}/ingest/dashboard/kpis`);
  if (!res.ok) throw new Error("Failed to fetch dashboard KPIs");

  const data = await res.json();

  return {
    videos_analyzed: data.videos_analyzed ?? data.total_videos ?? 0,
    trending_topics: data.trending_topics ?? data.total_trends ?? 0,
    avg_sentiment: data.avg_sentiment ?? 0,
    channels_tracked: data.channels_tracked ?? data.total_channels ?? 0,
    videos_this_week: data.videos_this_week ?? 0,
    topics_since_yesterday: data.topics_since_yesterday ?? 0,
  };
}

export async function getLeagueStats() {
  const res = await fetch(`${API_BASE}/ingest/dashboard/leagues`);
  if (!res.ok) throw new Error("Failed to fetch league stats");

  const data = await res.json();

  return {
    leagues: data.leagues || data.data || [],
  };
}

export async function getChannels() {
  const res = await fetch(`${API_BASE}/ingest/channels`);
  if (!res.ok) throw new Error("Failed to fetch channels");
  return res.json();
}

export async function getSentimentHistory() {
  const res = await fetch(`${API_BASE}/ingest/dashboard/sentiment-history`);
  if (!res.ok) throw new Error("Failed to fetch sentiment history");
  return res.json();
}

export async function getTrendsHistory() {
  const res = await fetch(`${API_BASE}/ingest/trends/history`);
  if (!res.ok) throw new Error("Failed to fetch trends history");
  return res.json();
}

export async function getChannelLatestVideo(channelId: string) {
  const res = await fetch(`${API_BASE}/ingest/channels/${channelId}/latest-video`);
  if (!res.ok) throw new Error("Failed to fetch channel latest video");
  return res.json();
}

export async function getEvents(limit?: number) {
  const searchParams = new URLSearchParams();
  if (limit) searchParams.set("limit", limit.toString());

  try {
    const res = await fetch(`${API_BASE}/ingest/events?${searchParams.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch events");

    const data = await res.json();
    return { events: data.events || data.data || [] };
  } catch {
    return { events: [] };
  }
}

// ============== Creator Risk Endpoints ==============

export async function getChannelRisk(channelId: string) {
  const res = await fetch(`${API_BASE}/ingest/channels/${channelId}/risk`);
  if (!res.ok) throw new Error("Failed to fetch channel risk");
  return res.json();
}

export async function getChannelsWithRisk(params?: {
  risk_level?: string;
  min_risk_score?: number;
  max_risk_score?: number;
  limit?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params?.risk_level) searchParams.set("risk_level", params.risk_level);
  if (params?.min_risk_score !== undefined) searchParams.set("min_risk_score", params.min_risk_score.toString());
  if (params?.max_risk_score !== undefined) searchParams.set("max_risk_score", params.max_risk_score.toString());
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  const res = await fetch(`${API_BASE}/ingest/channels/risk?${searchParams.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch channels with risk");
  return res.json();
}

export async function getVideosWithRisk(params?: {
  channel_id?: string;
  min_risk_score?: number;
  limit?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params?.channel_id) searchParams.set("channel_id", params.channel_id);
  if (params?.min_risk_score !== undefined) searchParams.set("min_risk_score", params.min_risk_score.toString());
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  const res = await fetch(`${API_BASE}/ingest/videos/risk?${searchParams.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch videos with risk");
  return res.json();
}