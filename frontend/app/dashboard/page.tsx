"use client";
import { useEffect, useState } from "react";
import Skeleton from "../components/skeleton";
import Card from "../components/card";
import CardHeader from "../components/cardHeader";
import KpiCard from "../components/kpiCard";
import VideoRow from "../components/videoRow";
import EventRow from "../components/eventRow";
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
  view_count: number;
  like_count: number;
  comment_count: number;
  duration_seconds: number;
  publish_date: string;
};

type Event = {
  id: string;
  event_type: string;
  description: string;
  created_at: string;
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
  if (val >= 60) return "pos";
  if (val >= 40) return "neu";
  return "neg";
}

function getSentimentLabel(value: number) {
  if (value >= 60) return "Positive";
  if (value >= 40) return "Neutral";
  return "Negative";
}

function getEventIcon(eventType: string) {
  switch (eventType) {
    case "goal":     return <Sparkles className="h-3.5 w-3.5 text-emerald-400" />;
    case "red_card": return <AlertTriangle className="h-3.5 w-3.5 text-red-400" />;
    case "injury":   return <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />;
    case "var":      return <TrendingUp className="h-3.5 w-3.5 text-sky-400" />;
    default:         return <Sparkles className="h-3.5 w-3.5 text-neutral-500" />;
  }
}

const leagueCodeMap: Record<string, string> = {
  "Premier League": "ENG",
  "La Liga": "ESP",
  Bundesliga: "GER",
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

function EventSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="divide-y divide-white/4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-3 px-6 py-4">
          <Skeleton className="h-6 w-6 shrink-0 rounded-md" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-3.5 w-4/5" />
            <Skeleton className="h-3 w-16" />
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

const ALL_LEAGUES = ["All", "Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"];
const FETCH_TIMEOUT_MS = 5000;

export default function DashboardPage() {
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [leagues, setLeagues] = useState<League[]>([]);
  const [videos, setVideos] = useState<VideoData[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [sentimentHistory, setSentimentHistory] = useState<SentimentData[]>([]);
  const [loading, setLoading] = useState(true);
  const [kpisError, setKpisError] = useState(false);
  const [leaguesError, setLeaguesError] = useState(false);
  const [videosError, setVideosError] = useState(false);
  const [eventsError, setEventsError] = useState(false);
  const [sentimentError, setSentimentError] = useState(false);
  const [activeLeague, setActiveLeague] = useState("All");

  const animatedVideos    = useCountUp(kpis?.videos_analyzed   ?? null);
  const animatedTopics    = useCountUp(kpis?.trending_topics   ?? null);
  const animatedChannels  = useCountUp(kpis?.channels_tracked  ?? null);
  const animatedSentiment = useCountUp(kpis?.avg_sentiment     ?? null);

  useEffect(() => {
    async function fetchData() {
      const withTimeout = <T,>(p: Promise<T>, label: string): Promise<T> =>
        Promise.race([
          p,
          new Promise<T>((_, reject) =>
            setTimeout(() => reject(new Error(`Timeout: ${label}`)), FETCH_TIMEOUT_MS)
          ),
        ]);

      const [kpiRes, leagueRes, videoRes, eventsRes, sentimentRes] =
        await Promise.allSettled([
          withTimeout(getDashboardKPIs(),           "getDashboardKPIs"),
          withTimeout(getLeagueStats(),             "getLeagueStats"),
          withTimeout(getVideos({ limit: 10 }),     "getVideos"),
          withTimeout(getEvents(5),                 "getEvents"),
          withTimeout(getSentimentHistory(),        "getSentimentHistory"),
        ]);

      if (kpiRes.status === "fulfilled") {
        setKpis(kpiRes.value);
      } else {
        console.error("[Dashboard] KPIs failed:", kpiRes.reason);
        setKpisError(true);
      }

      if (leagueRes.status === "fulfilled") {
        setLeagues(leagueRes.value.leagues || []);
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

      if (eventsRes.status === "fulfilled") {
        setEvents(eventsRes.value.events || []);
      } else {
        // Events are non-fatal — warn rather than error since the endpoint may not exist
        console.warn("[Dashboard] Events failed (non-fatal):", eventsRes.reason);
        setEventsError(true);
      }

      if (sentimentRes.status === "fulfilled") {
        const formatted = (sentimentRes.value.weeks || []).map(
          (w: any, i: number) => ({
            ...w,
            week: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][i % 7] || w.week,
          })
        );
        setSentimentHistory(formatted);
      } else {
        console.error("[Dashboard] Sentiment history failed:", sentimentRes.reason);
        setSentimentError(true);
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

      <div className="relative z-10 mx-auto max-w-6xl px-6 py-12">

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
            Real-time YouTube intelligence across top soccer channels
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
            sub={kpiSub(kpisError, `+${kpis?.videos_this_week ?? 0} this week`)}
            loading={loading}
          />
          <KpiCard
            icon={<TrendingUp className="h-3.5 w-3.5" />}
            title="Trending Topics"
            value={kpisError ? "—" : kpis ? formatNumber(animatedTopics) : "—"}
            sub={kpiSub(kpisError, `+${kpis?.topics_since_yesterday ?? 0} since yesterday`)}
            loading={loading}
          />
          <KpiCard
            icon={<Activity className="h-3.5 w-3.5" />}
            title="Avg. Sentiment"
            value={kpisError ? "—" : kpis ? `${Math.round(animatedSentiment)}%` : "—"}
            sub={kpiSub(kpisError, kpis ? getSentimentLabel(kpis.avg_sentiment) + " overall" : "—")}
            loading={loading}
          />
          <KpiCard
            icon={<Users className="h-3.5 w-3.5" />}
            title="Channels Tracked"
            value={kpisError ? "—" : kpis ? formatNumber(animatedChannels) : "—"}
            sub={kpiSub(kpisError, leagues.length ? `${leagues.length} leagues` : "No leagues")}
            loading={loading}
          />
        </div>

        {/* ── Sentiment + Events ── */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2 flex flex-col">
            <CardHeader
              title="Sentiment Trend"
              subtitle="Weekly fan sentiment across all leagues"
              right={
                <div className="flex items-center gap-4 text-[11px] text-neutral-500">
                  <span className="flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
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
                <div className="h-full">
                  <SentimentChart data={sentimentHistory} />
                </div>
              )}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Key Events"
              subtitle="Highlights detected across leagues"
            />
            <div className="divide-y divide-white/4">
              {loading ? (
                <EventSkeleton />
              ) : eventsError ? (
                <EmptyState message="Failed to load events" />
              ) : events.length === 0 ? (
                <EmptyState message="No events available" />
              ) : (
                events.map((event) => (
                  <EventRow
                    key={event.id}
                    icon={getEventIcon(event.event_type)}
                    title={event.description}
                    time={getRelativeTime(event.created_at)}
                  />
                ))
              )}
            </div>
          </Card>
        </div>

        {/* ── Videos + League Overview ── */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader
              title="Trending Match Content"
              subtitle="Most engaging soccer content from tracked channels"
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
            <div className="divide-y divide-white/4">
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
                    league={video.league || "Unknown"}
                    sentiment={`${Math.round(kpis?.avg_sentiment ?? 0)}%`}
                    sentimentTone={sentimentTone}
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
          </Card>

          <Card>
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
                leagues.map((league) => (
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
