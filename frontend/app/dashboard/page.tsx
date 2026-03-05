"use client";
import Card from "../components/card";
import CardHeader from "../components/cardHeader";
import KpiCard from "../components/kpiCard";

import {
  TrendingUp,
  Video,
  Activity,
  Users,
  ArrowUpRight,
  ArrowDownRight,
  Play,
  Clock,
  Eye,
  ThumbsUp,
  MessageSquare,
  Sparkles,
  AlertTriangle,
} from "lucide-react";

export default function DashboardPage() {
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
            value="1,247"
            sub="+83 this week"
            trend="up"
            icon={<Video className="h-4 w-4 text-neutral-400" />}
          />
          <KpiCard
            title="Trending Topics"
            value="34"
            sub="+12 since yesterday"
            trend="up"
            icon={<TrendingUp className="h-4 w-4 text-neutral-400" />}
          />
          <KpiCard
            title="Avg. Sentiment"
            value="72%"
            sub="+4.2% positive"
            trend="up"
            icon={<Activity className="h-4 w-4 text-neutral-400" />}
          />
          <KpiCard
            title="Channels Tracked"
            value="18"
            sub="5 leagues"
            trend="flat"
            icon={<Users className="h-4 w-4 text-neutral-400" />}
          />
        </div>

        {/* Main Grid */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Sentiment Trend (mock chart) */}
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
              <div className="relative h-64 w-full overflow-hidden rounded-xl border border-neutral-800 bg-neutral-950">
                {/* grid lines */}
                <div className="absolute inset-0 opacity-60">
                  <div className="h-full w-full bg-[linear-gradient(to_right,rgba(255,255,255,0.06)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.06)_1px,transparent_1px)] bg-[size:56px_56px]" />
                </div>

                {/* Positive line (SVG) */}
                <svg className="absolute inset-0 h-full w-full" viewBox="0 0 700 260" preserveAspectRatio="none">
                  <path
                    d="M0,150 C80,120 120,110 180,120 C240,135 270,175 330,165 C400,150 420,110 480,118 C540,126 590,105 700,118"
                    fill="none"
                    stroke="rgb(56 189 248)" // sky-400
                    strokeWidth="2.5"
                  />
                  <path
                    d="M0,150 C80,120 120,110 180,120 C240,135 270,175 330,165 C400,150 420,110 480,118 C540,126 590,105 700,118 L700,260 L0,260 Z"
                    fill="rgba(56,189,248,0.10)"
                  />
                </svg>

                {/* Negative line */}
                <svg className="absolute inset-0 h-full w-full" viewBox="0 0 700 260" preserveAspectRatio="none">
                  <path
                    d="M0,210 C90,230 150,240 210,220 C270,200 310,175 360,195 C410,215 460,230 520,225 C600,218 640,210 700,205"
                    fill="none"
                    stroke="rgb(239 68 68)" // red-500
                    strokeWidth="2.5"
                  />
                  <path
                    d="M0,210 C90,230 150,240 210,220 C270,200 310,175 360,195 C410,215 460,230 520,225 C600,218 640,210 700,205 L700,260 L0,260 Z"
                    fill="rgba(239,68,68,0.10)"
                  />
                </svg>

                {/* x labels */}
                <div className="absolute bottom-3 left-0 right-0 flex justify-between px-6 text-[11px] text-neutral-500">
                  <span>Mon</span>
                  <span>Tue</span>
                  <span>Wed</span>
                  <span>Thu</span>
                  <span>Fri</span>
                  <span>Sat</span>
                  <span>Sun</span>
                </div>

                {/* y labels */}
                <div className="absolute left-3 top-3 flex h-[calc(100%-44px)] flex-col justify-between text-[11px] text-neutral-500">
                  <span>100%</span>
                  <span>75%</span>
                  <span>50%</span>
                  <span>25%</span>
                  <span>0%</span>
                </div>
              </div>
            </div>
          </Card>

          {/* Key Events */}
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
              <VideoRow
                league="Premier League"
                sentiment="positive 84%"
                sentimentTone="pos"
                title="Arsenal vs Manchester City — Premier League Highlights"
                channel="Sky Sports Football"
                duration="12:34"
                views="2.4M"
                likes="89K"
                comments="12K"
                age="6 hours ago"
              />

              <VideoRow
                league="La Liga"
                sentiment="positive 91%"
                sentimentTone="pos"
                title="Real Madrid vs Barcelona — El Clasico Full Analysis"
                channel="LaLiga Official"
                duration="15:21"
                views="3.1M"
                likes="120K"
                comments="18K"
                age="12 hours ago"
              />

              <VideoRow
                league="Bundesliga"
                sentiment="neutral 62%"
                sentimentTone="neu"
                title="Bayern Munich vs Dortmund — Der Klassiker Recap"
                channel="Bundesliga"
                duration="11:45"
                views="1.8M"
                likes="67K"
                comments="8K"
                age="1 day ago"
              />

              <VideoRow
                league="Serie A"
                sentiment="negative 38%"
                sentimentTone="neg"
                title="Napoli vs Inter Milan — Title Race Decider"
                channel="Serie A Official"
                duration="13:09"
                views="1.2M"
                likes="45K"
                comments="6K"
                age="2 days ago"
              />
            </div>
          </Card>

          {/* League Overview */}
          <Card>
            <CardHeader title="League Overview" subtitle="Content volume & status by league" />
            <div className="divide-y divide-neutral-800">
              <LeagueRow code="ENG" league="Premier League" count="412" status="Trending" />
              <LeagueRow code="ESP" league="La Liga" count="287" status="Trending" />
              <LeagueRow code="GER" league="Bundesliga" count="198" status="" />
              <LeagueRow code="ITA" league="Serie A" count="189" status="" />
              <LeagueRow code="FRA" league="Ligue 1" count="161" status="Trending" />
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