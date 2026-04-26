"use client";
import { useEffect, useState } from "react";
import Skeleton from "../components/skeleton";
import Card from "../components/card";
import CardHeader from "../components/cardHeader";
import KpiCard from "../components/kpiCard";
import VideoRow from "../components/videoRow";
import LeagueRow from "../components/leagueRow";
import SectionLabel from "../components/sectionLabel";
import EmptyState from "../components/emptyState";
import SentimentChart from "../components/sentimentChart";
import {
  getDashboardKPIs,
  getLeagueStats,
  getVideos,
  getEvents,
  getSentimentHistory,
  getTrends,
  getNarratives,
} from "../../api/backend";

import {
  TrendingUp,
  Video,
  Activity,
  Users,
  Sparkles,
  AlertTriangle,
} from "lucide-react";

/* ---------------- Types ---------------- */

type KPIs = {
  videos_analyzed: number;
  trending_topics: number;
  avg_sentiment: number;
  channels_tracked: number;
  videos_this_week: number;
  topics_since_yesterday: number;
  trending_claims: number;
};

type League = {
  league: string;
  count: number;
  status: string;
};

type VideoData = {
  video_id: string;
  title: string;
  channel_name: string;
  league: string | null;
  teams: string[] | null;
  view_count: number;
  like_count: number;
  comment_count: number;
  duration_seconds: number;
  publish_date: string;
  sentiment_pct: number | null;
};

type SentimentData = {
  week: string;
  positive: number;
  negative: number;
};

/* ---------------- Helpers ---------------- */

function useCountUp(target: number | null, duration = 1200) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (target === null) return;

    const finalTarget = target;
    const startTime = performance.now();

    function animate(now: number) {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.floor(eased * finalTarget));
      if (progress < 1) requestAnimationFrame(animate);
    }

    requestAnimationFrame(animate);
  }, [target, duration]);

  return value;
}

function formatNumber(num: number): string {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toLocaleString();
}

function formatDuration(seconds: number): string {
  if (!seconds) return "--:--";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function getRelativeTime(dateStr: string): string {
  if (!dateStr) return "Unknown";
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);
  if (diffHours < 1) return "Just now";
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return "1 day ago";
  return `${diffDays} days ago`;
}

function getSentimentTone(val: number): "pos" | "neu" | "neg" {
  if (val >= 0.6) return "pos";
  if (val >= 0.4) return "neu";
  return "neg";
}

function getSentimentLabel(value: number) {
  if (value >= 0.6) return "Positive";
  if (value >= 0.4) return "Neutral";
  return "Negative";
}

const leagueCodeMap: Record<string, string> = {
  "Premier League": "ENG",
  "Champions League": "UCL",
  "La Liga": "ESP",
  "Bundesliga": "GER",
  "Serie A": "ITA",
  "Ligue 1": "FRA",
};

/* ─── Loading skeletons for lists ─── */

function ListSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="divide-y divide-white/4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 px-6 py-4">
          <Skeleton className="h-18 w-32 shrink-0" />
          <div className="flex flex-1 flex-col gap-2 py-1">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-4 w-4/5" />
            <Skeleton className="h-3 w-24" />
          </div>
        </div>
      ))}
    </div>
  );
}

function LeagueSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="divide-y divide-white/4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <Skeleton className="h-6 w-9 rounded-md" />
            <Skeleton className="h-3.5 w-24" />
          </div>
          <Skeleton className="h-5 w-16 rounded-md" />
        </div>
      ))}
    </div>
  );
}

/* ================================================================
   PAGE
================================================================ */

const ALL_LEAGUES = ["All", "Premier League", "Champions League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"];
const FETCH_TIMEOUT_MS = 15000;

export default function DashboardPage() {
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [leagues, setLeagues] = useState<League[]>([]);
  const [videos, setVideos] = useState<VideoData[]>([]);
  const [sentimentHistory, setSentimentHistory] = useState<SentimentData[]>([]);
  const [topNarratives, setTopNarratives] = useState<{ title: string; score: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [kpisError, setKpisError] = useState(false);
  const [leaguesError, setLeaguesError] = useState(false);
  const [videosError, setVideosError] = useState(false);
  const [narrativesError, setNarrativesError] = useState(false);
  const [sentimentError, setSentimentError] = useState(false);
  const [activeLeague, setActiveLeague] = useState("All");

  const animatedVideos    = useCountUp(kpis?.videos_analyzed   ?? null);
  const animatedTopics    = useCountUp(kpis?.trending_topics   ?? null);
  const animatedChannels  = useCountUp(kpis?.channels_tracked  ?? null);
  const animatedClaims    = useCountUp(kpis?.trending_claims   ?? null);

  useEffect(() => {
    async function fetchData() {
      const withTimeout = <T,>(p: Promise<T>, label: string): Promise<T> =>
        Promise.race([
          p,
          new Promise<T>((_, reject) =>
            setTimeout(() => reject(new Error(`Timeout: ${label}`)), FETCH_TIMEOUT_MS)
          ),
        ]);

      const [kpiRes, leagueRes, videoRes, sentimentRes, trendsRes, narrativesRes] =
        await Promise.allSettled([
          withTimeout(getDashboardKPIs(),           "getDashboardKPIs"),
          withTimeout(getLeagueStats(),             "getLeagueStats"),
          withTimeout(getVideos({ limit: 30 }),     "getVideos"),
          withTimeout(getSentimentHistory(),        "getSentimentHistory"),
          withTimeout(getTrends({ limit: 5 }),     "getTrends"),
          withTimeout(getNarratives(),              "getNarratives"),
        ]);

      if (kpiRes.status === "fulfilled") {
        setKpis(kpiRes.value);
      } else {
        console.error("[Dashboard] KPIs failed:", kpiRes.reason);
        setKpisError(true);
      }

      if (leagueRes.status === "fulfilled") {
        const ALL_KNOWN_LEAGUES = [
          "Premier League",
          "Champions League",
          "La Liga",
          "Bundesliga",
          "Serie A",
          "Ligue 1",
        ];
        const fetched = (leagueRes.value.leagues || []).filter((l: League) => l.league !== "Unknown");
        const fetchedNames = new Set(fetched.map((l: League) => l.league));
        const merged = [
          ...fetched,
          ...ALL_KNOWN_LEAGUES
            .filter((name) => !fetchedNames.has(name))
            .map((name) => ({ league: name, count: 0, status: "" })),
        ];
        setLeagues(merged);
      } else {
        console.error("[Dashboard] League stats failed:", leagueRes.reason);
        setLeaguesError(true);
      }

      if (videoRes.status === "fulfilled") {
        setVideos(videoRes.value.videos || []);
      } else {
        console.error("[Dashboard] Videos failed:", videoRes.reason);
        setVideosError(true);
      }

      if (sentimentRes.status === "fulfilled") {
        const formatted = (sentimentRes.value.weeks || []).map(
          (w: any, i: number) => ({
            ...w,
            week: w.week && /^week\s*\d+/i.test(w.week)
              ? `${i + 1} wk ago`
              : w.week || `${i + 1} wk ago`,
            positive: (w.positive ?? 0),
            negative: (w.negative ?? 0),
          })
        );
        setSentimentHistory([...formatted].reverse());
      } else {
        console.error("[Dashboard] Sentiment history failed:", sentimentRes.reason);
        setSentimentError(true);
      }

      if (trendsRes.status === "fulfilled" && narrativesRes.status === "fulfilled") {
        const narrativeMap = new Map<string, string>(
          (narrativesRes.value.narratives || []).map((n: any) => [n.id, n.title])
        );
        const top = (trendsRes.value.trends || [])
          .map((t: any) => ({
            title: narrativeMap.get(t.narrative_id) || "Unknown",
            score: Math.round(t.score * 100),
          }));
        setTopNarratives(top);
      } else {
        console.error("[Dashboard] Trends/narratives failed:", trendsRes, narrativesRes);
        setNarrativesError(true);
      }

      setLoading(false);
    }
    fetchData();
  }, []);

  const sentimentTone = kpis ? getSentimentTone(kpis.avg_sentiment) : "neu";
  const filteredVideos =
    activeLeague === "All"
      ? videos
      : videos.filter((v) => v.league === activeLeague);

  /* ── KPI sub-text helpers (guards against null/error/loading) ── */
  function kpiSub(errorFlag: boolean, loadedValue: string): string {
    if (errorFlag) return "Failed to load";
    if (loading)   return "Loading…";
    return loadedValue;
  }

  return (
    <div className="relative min-h-screen w-full overflow-x-hidden bg-[#080808] text-white">

      {/* ── Grid background ── */}
      <div className="pointer-events-none fixed inset-0 z-0 opacity-[0.03]">
        <div
          className="h-full w-full"
          style={{
            backgroundImage: `
              linear-gradient(to right, white 1px, transparent 1px),
              linear-gradient(to bottom, white 1px, transparent 1px)
            `,
            backgroundSize: "80px 80px",
          }}
        />
      </div>

      <div className="relative z-10 mx-auto max-w-7xl px-6 py-12">

        {/* ── Page header ── */}
        <div className="mb-10">
          <SectionLabel>Overview</SectionLabel>
          <h1
            className="mt-2 text-[clamp(2rem,4vw,2.8rem)] font-black leading-tight tracking-[-0.02em]"
            style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
          >
            Dashboard
          </h1>
          <p className="mt-2 text-sm text-neutral-500">
            On-demand YouTube intelligence across top soccer channels
          </p>
        </div>

        {/* ── accent line ── */}
        <div className="mb-6 h-px w-full bg-linear-to-r from-transparent via-teal-500/30 to-transparent" />

        {/* ── KPIs ── */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <KpiCard
            icon={<Video className="h-3.5 w-3.5" />}
            title="Videos Analyzed"
            value={kpisError ? "—" : kpis ? formatNumber(animatedVideos) : "—"}
            sub={kpiSub(kpisError, kpis ? `+${kpis.videos_this_week} this week` : "Loading…")}
            loading={loading}
          />
          <KpiCard
            icon={<TrendingUp className="h-3.5 w-3.5" />}
            title="Trends Identified"
            value={kpisError ? "—" : kpis ? formatNumber(animatedTopics) : "—"}
            sub={kpiSub(kpisError, kpis ? `+${kpis.topics_since_yesterday} since yesterday` : "Loading…")}
            loading={loading}
          />
          <KpiCard
            icon={<Activity className="h-3.5 w-3.5" />}
            title="Claims Extracted"
            value={kpisError ? "—" : kpis ? formatNumber(animatedClaims) : "—"}
            sub={kpiSub(kpisError, "From transcripts & comments")}
            loading={loading}
          />
          <KpiCard
            icon={<Users className="h-3.5 w-3.5" />}
            title="Channels Tracked"
            value={kpisError ? "—" : kpis ? formatNumber(animatedChannels) : "—"}
            sub={kpiSub(kpisError, "Across 6 leagues")}
            loading={loading}
          />
        </div>

        {/* ── Sentiment + Trend Scores ── */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2 flex flex-col">
            <CardHeader
              title="Sentiment Trend"
              subtitle="Weekly fan sentiment across all videos"
              right={
                <div className="flex items-center gap-4 text-[11px] text-neutral-500 mt-6">
                  <span className="flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    Positive
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                    Negative
                  </span>
                </div>
              }
            />
            <div className="flex-1 px-6 pb-6 pt-4">
              {loading ? (
                <Skeleton className="h-56 w-full" />
              ) : sentimentError ? (
                <EmptyState message="Failed to load sentiment data" />
              ) : sentimentHistory.length === 0 ? (
                <EmptyState message="No sentiment data available" />
              ) : (
                <SentimentChart data={sentimentHistory} />
              )}
            </div>
          </Card>

          <Card className="lg:col-span-1 flex flex-col min-h-125">
            <CardHeader
              title="Top Narratives"
              subtitle="Highest scoring narratives by trend score"
            />
            <div className="flex-1 px-6 pb-6 pt-2">
              {loading ? (
                <Skeleton className="h-56 w-full" />
              ) : narrativesError ? (
                <EmptyState message="Failed to load narratives" />
              ) : topNarratives.length === 0 ? (
                <EmptyState message="No narrative data available" />
              ) : (
                <div className="flex flex-col justify-between h-full">
                  {topNarratives.map((n, i) => {
                    const barColor =
                      n.score >= 65
                        ? "bg-emerald-400"
                        : n.score >= 40
                        ? "bg-amber-400"
                        : "bg-red-400";
                    const scoreColor =
                      n.score >= 65
                        ? "text-emerald-400"
                        : n.score >= 40
                        ? "text-amber-400"
                        : "text-red-400";
                    return (
                      <div key={i} className="flex flex-col gap-1.5 py-3 border-b border-white/4 last:border-0">
                        <div className="flex items-center justify-between gap-2">
                          <span
                            className="truncate text-[13px] font-medium text-white/85 leading-snug"
                            title={n.title}
                          >
                            {n.title}
                          </span>
                          <span className="shrink-0 tabular-nums text-[11px] text-neutral-400 w-7 text-right">
                            {n.score}%
                          </span>
                        </div>
                        <div className="h-1 w-full rounded-full bg-white/8 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-700 ${barColor}`}
                            style={{ width: `${Math.min(n.score, 100)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* ── Videos + League Overview ── */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2 flex flex-col min-h-125">
            <CardHeader
              title="Trending Match Content"
              subtitle="Most watched soccer content from tracked channels"
            />
            {/* League filter tabs */}
            <div className="flex gap-1 overflow-x-auto border-b border-white/6 px-6 pb-0 pt-3 scrollbar-none">
              {ALL_LEAGUES.map((lg) => (
                <button
                  key={lg}
                  onClick={() => setActiveLeague(lg)}
                  className={[
                    "relative shrink-0 rounded-t-md px-3.5 py-2 text-[12px] font-medium transition-colors duration-150",
                    activeLeague === lg
                      ? "text-white"
                      : "text-neutral-500 hover:text-neutral-300",
                  ].join(" ")}
                >
                  {activeLeague === lg && (
                    <span className="absolute inset-0 rounded-t-md bg-white/5 ring-1 ring-inset ring-white/[0.07]" />
                  )}
                  {activeLeague === lg && (
                    <span className="absolute bottom-0 left-1/2 h-px w-5 -translate-x-1/2 rounded-full bg-teal-400/80" />
                  )}
                  <span className="relative">{lg}</span>
                </button>
              ))}
            </div>
            <div
              className="divide-y divide-white/4 overflow-y-scroll"
              style={{
                minHeight: "calc(3 * 120px)",
                maxHeight: "calc(3 * 120px)",
                scrollbarWidth: "thin",
                scrollbarColor: "rgba(255,255,255,0.20) rgba(255,255,255,0.04)",
              }}
            >
              {loading ? (
                <ListSkeleton />
              ) : videosError ? (
                <EmptyState message="Failed to load videos" />
              ) : filteredVideos.length === 0 ? (
                <EmptyState
                  message={
                    activeLeague === "All"
                      ? "No videos available"
                      : `No ${activeLeague} videos available`
                  }
                />
              ) : (
                filteredVideos.map((video) => (
                  <VideoRow
                    key={video.video_id}
                    videoId={video.video_id}
                    league={video.league || ""}
                    teams={video.teams || []}
                    sentiment={video.sentiment_pct != null ? `${Math.round(video.sentiment_pct * 100)}%` : "N/A"}
                    sentimentTone={video.sentiment_pct != null ? (video.sentiment_pct >= 0.6 ? "pos" : video.sentiment_pct >= 0.4 ? "neu" : "neg") : "neu"}
                    title={video.title}
                    channel={video.channel_name || "Unknown channel"}
                    duration={formatDuration(video.duration_seconds)}
                    views={formatNumber(video.view_count)}
                    likes={formatNumber(video.like_count)}
                    comments={formatNumber(video.comment_count)}
                    age={getRelativeTime(video.publish_date)}
                  />
                ))
              )}
            </div>
            {!loading && !videosError && (
              <div className="border-t border-white/4 px-6 py-3">
                <span className="text-[11px] text-neutral-600">
                  Showing {filteredVideos.length} of {videos.length} videos
                  {activeLeague !== "All" && ` · filtered by ${activeLeague}`}
                </span>
              </div>
            )}
          </Card>

          <Card className="self-start">
            <CardHeader
              title="League Overview"
              subtitle="Content volume & status by league"
            />
            <div className="divide-y divide-white/4">
              {loading ? (
                <LeagueSkeleton />
              ) : leaguesError ? (
                <EmptyState message="Failed to load leagues" />
              ) : leagues.length === 0 ? (
                <EmptyState message="No leagues available" />
              ) : (
                [...leagues]
                  .filter((l) =>
                    ["Premier League", "Champions League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"].includes(l.league)
                  )
                  .sort((a, b) => {
                    const order = [
                      "Premier League",
                      "Champions League",
                      "La Liga",
                      "Bundesliga",
                      "Serie A",
                      "Ligue 1",
                    ];
                    return order.indexOf(a.league) - order.indexOf(b.league);
                  })
                  .map((league) => (
                  <LeagueRow
                    key={league.league}
                    code={
                      leagueCodeMap[league.league] ||
                      league.league?.slice(0, 3).toUpperCase() ||
                      "UNK"
                    }
                    league={league.league}
                    count={league.count.toString()}
                    status={league.status}
                  />
                ))
              )}
            </div>
          </Card>
        </div>

      </div>
    </div>
  );
}
