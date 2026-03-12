"use client";
import { useEffect, useState } from "react";
import Card from "../components/card";
import CardHeader from "../components/cardHeader";
import KpiCard from "../components/kpiCard";
import SentimentChart from "../components/sentimentChart";
import { getDashboardKPIs, getLeagueStats, getVideos } from "../../api/backend";

import {
  TrendingUp,
  Video,
  Activity,
  Users,
  Play,
  Clock,
  Eye,
  ThumbsUp,
  MessageSquare,
  Sparkles,
  AlertTriangle,
} from "lucide-react";

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

export default function DashboardPage() {
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [leagues, setLeagues] = useState<League[]>([]);
  const [videos, setVideos] = useState<VideoData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [kpiRes, leagueRes, videoRes] = await Promise.all([
          getDashboardKPIs(),
          getLeagueStats(),
          getVideos({ limit: 10 }),
        ]);
        setKpis(kpiRes);
        setLeagues(leagueRes.leagues || []);
        setVideos(videoRes.videos || []);
      } catch (err) {
        console.error("Failed to fetch dashboard data:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const leagueCodeMap: Record<string, string> = {
    "Premier League": "ENG",
    "La Liga": "ESP",
    Bundesliga: "GER",
    "Serie A": "ITA",
    "Ligue 1": "FRA",
  };

  const formatNumber = (num: number): string => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toString();
  };

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const getSentimentTone = (): "pos" | "neu" | "neg" => {
    if (!kpis) return "neu";
    if (kpis.avg_sentiment >= 70) return "pos";
    if (kpis.avg_sentiment >= 40) return "neu";
    return "neg";
  };

  const getRelativeTime = (dateStr: string): string => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) return "Just now";
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return "1 day ago";
    return `${diffDays} days ago`;
  };

  return (
    <div className="min-h-screen w-full bg-black text-white">
      <div className="mx-auto max-w-6xl px-6 py-10">
        {/* Header */}
        <div className="mb-8">
          <div className="text-sm text-neutral-400">Real-time sports intelligence from YouTube content analysis</div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Dashboard</h1>
        </div>

        {/* KPI Row */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <KpiCard
            title="Videos Analyzed"
            value={kpis ? kpis.videos_analyzed.toLocaleString() : "..."}
            sub={kpis ? `+${kpis.videos_this_week} this week` : ""}
            trend="up"
            icon={<Video className="h-4 w-4 text-neutral-400" />}
          />
          <KpiCard
            title="Trending Topics"
            value={kpis ? kpis.trending_topics.toString() : "..."}
            sub={kpis ? `+${kpis.topics_since_yesterday} since yesterday` : ""}
            trend="up"
            icon={<TrendingUp className="h-4 w-4 text-neutral-400" />}
          />
          <KpiCard
            title="Avg. Sentiment"
            value={kpis ? `${Math.round(kpis.avg_sentiment)}%` : "..."}
            sub="+4.2% positive"
            trend="up"
            icon={<Activity className="h-4 w-4 text-neutral-400" />}
          />
          <KpiCard
            title="Channels Tracked"
            value={kpis ? kpis.channels_tracked.toString() : "..."}
            sub={`${leagues.length} leagues`}
            trend="flat"
            icon={<Users className="h-4 w-4 text-neutral-400" />}
          />
        </div>

        {/* Main Grid */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Sentiment Trend (real chart) */}
          <Card className="lg:col-span-2">
            <CardHeader
              title="Sentiment Trend"
              subtitle="Weekly fan sentiment across all leagues"
              right={
                <div className="flex items-center gap-4 text-xs text-neutral-400">
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-sky-400" />
                    Positive
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-red-500" />
                    Negative
                  </span>
                </div>
              }
            />
            <div className="px-5 pb-5">
              <SentimentChart />
            </div>
          </Card>

          {/* Key Events - Mock data as per user request */}
          <Card>
            <CardHeader title="Key Events" subtitle="Highlights detected across tracked leagues" />
            <div className="divide-y divide-neutral-800">
              <EventRow
                icon={<Sparkles className="h-4 w-4 text-emerald-400" />}
                title="Saka scores for Arsenal vs Man City (23')"
                time="6h ago"
              />
              <EventRow
                icon={<TrendingUp className="h-4 w-4 text-sky-400" />}
                title="VAR overturns penalty in El Clasico"
                time="12h ago"
              />
              <EventRow
                icon={<AlertTriangle className="h-4 w-4 text-red-400" />}
                title="Red card: Rodri tackle in 78th minute"
                time="6h ago"
              />
              <EventRow
                icon={<AlertTriangle className="h-4 w-4 text-amber-400" />}
                title="Musiala subbed off with hamstring injury"
                time="1d ago"
              />
              <EventRow
                icon={<Sparkles className="h-4 w-4 text-emerald-400" />}
                title="Kane hat-trick vs Dortmund"
                time="1d ago"
              />
            </div>
          </Card>
        </div>

        {/* Lower Grid */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Trending Match Content */}
          <Card className="lg:col-span-2">
            <CardHeader title="Trending Match Content" subtitle="Most engaging soccer content from tracked channels" />
            <div className="divide-y divide-neutral-800">
              {loading || videos.length === 0 ? (
                <div className="px-5 py-10 text-center text-sm text-neutral-500">No videos available</div>
              ) : (
                videos.map((video) => (
                  <VideoRow
                    key={video.video_id}
                    league={video.league || "Unknown"}
                    sentiment={`positive ${Math.round(kpis?.avg_sentiment || 72)}%`}
                    sentimentTone={getSentimentTone()}
                    title={video.title}
                    channel={video.channel_name}
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

          {/* League Overview */}
          <Card>
            <CardHeader title="League Overview" subtitle="Content volume & status by league" />
            <div className="divide-y divide-neutral-800">
              {loading || leagues.length === 0 ? (
                <div className="px-5 py-10 text-center text-sm text-neutral-500">No leagues available</div>
              ) : (
                leagues.map((league) => (
                  <LeagueRow
                    key={league.league}
                    code={leagueCodeMap[league.league] || "UNK"}
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

/* ---------------- Components ---------------- */

function EventRow({ icon, title, time }: { icon: React.ReactNode; title: string; time: string }) {
  return (
    <div className="flex gap-3 px-5 py-4">
      <div className="mt-0.5">{icon}</div>
      <div className="min-w-0">
        <div className="truncate text-sm font-medium">{title}</div>
        <div className="text-xs text-neutral-500">{time}</div>
      </div>
    </div>
  );
}

function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "pos" | "neu" | "neg" }) {
  const cls =
    tone === "pos"
      ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/20"
      : tone === "neu"
      ? "bg-amber-500/15 text-amber-300 border-amber-500/20"
      : tone === "neg"
      ? "bg-red-500/15 text-red-300 border-red-500/20"
      : "bg-neutral-800/40 text-neutral-200 border-neutral-700";

  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] ${cls}`}>
      {children}
    </span>
  );
}

function VideoRow({
  league,
  sentiment,
  sentimentTone,
  title,
  channel,
  duration,
  views,
  likes,
  comments,
  age,
}: {
  league: string;
  sentiment: string;
  sentimentTone: "pos" | "neu" | "neg";
  title: string;
  channel: string;
  duration: string;
  views: string;
  likes: string;
  comments: string;
  age: string;
}) {
  return (
    <div className="flex gap-5 px-5 py-5">
      {/* thumb */}
      <div className="relative h-20 w-36 shrink-0 overflow-hidden rounded-xl border border-neutral-800 bg-gradient-to-br from-neutral-900 to-neutral-950">
        <div className="absolute inset-0 flex items-center justify-center">
          <Play className="h-6 w-6 text-neutral-400" />
        </div>
        <div className="absolute bottom-2 right-2 rounded bg-black/70 px-2 py-0.5 text-[11px] text-neutral-200">
          {duration}
        </div>
      </div>

      {/* content */}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="neutral">{league}</Badge>
          <Badge tone={sentimentTone}>{sentiment}</Badge>
        </div>

        <div className="mt-2 truncate text-sm font-semibold">{title}</div>
        <div className="mt-0.5 text-xs text-neutral-500">{channel}</div>

        <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-neutral-500">
          <span className="inline-flex items-center gap-1">
            <Eye className="h-3.5 w-3.5" /> {views}
          </span>
          <span className="inline-flex items-center gap-1">
            <ThumbsUp className="h-3.5 w-3.5" /> {likes}
          </span>
          <span className="inline-flex items-center gap-1">
            <MessageSquare className="h-3.5 w-3.5" /> {comments}
          </span>
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3.5 w-3.5" /> {age}
          </span>
        </div>
      </div>
    </div>
  );
}

function LeagueRow({ code, league, count, status }: { code: string; league: string; count: string; status: string }) {
  return (
    <div className="flex items-center justify-between gap-4 px-5 py-4">
      <div className="flex items-center gap-3 min-w-0">
        <span className="inline-flex h-7 w-9 items-center justify-center rounded-md bg-neutral-900 text-[10px] text-neutral-200 border border-neutral-800">
          {code}
        </span>
        <div className="truncate text-sm font-medium">{league}</div>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <div className="text-xs text-neutral-500">{count}</div>
        {status ? (
          <span className="rounded-md bg-sky-500/15 px-2 py-1 text-[11px] text-sky-300 border border-sky-500/20">
            {status}
          </span>
        ) : null}
      </div>
    </div>
  );
}
