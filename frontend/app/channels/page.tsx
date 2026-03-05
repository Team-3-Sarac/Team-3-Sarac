"use client";
import KpiCard from "../components/kpiCard";
import ChannelRow from "../components/channelRow";



import { useMemo, useState } from "react";

type Channel = {
  id: string;
  initials: string;
  name: string;
  handle: string;
  subs: string;
  league: string;
  videos: number;
  sentimentPct: number;
  sentimentDir: "up" | "down" | "flat";
  latestTitle: string;
  latestViews: string;
  active: boolean;
};

export default function ChannelsPage() {
  const [rows, setRows] = useState<Channel[]>([
    {
      id: "sky",
      initials: "SS",
      name: "Sky Sports Football",
      handle: "@SkySportsFootball",
      subs: "7.2M",
      league: "Premier League",
      videos: 142,
      sentimentPct: 74,
      sentimentDir: "up",
      latestTitle: "Arsenal vs Man City - Extended Highlights",
      latestViews: "2.4M views",
      active: true,
    },
    {
      id: "espnfc",
      initials: "E",
      name: "ESPNFC",
      handle: "@ESPNFC",
      subs: "5.1M",
      league: "Multi-League",
      videos: 98,
      sentimentPct: 68,
      sentimentDir: "flat",
      latestTitle: "Title Race Power Rankings - February Update",
      latestViews: "1.1M views",
      active: true,
    },
    {
      id: "laliga",
      initials: "LO",
      name: "LaLiga Official",
      handle: "@LaLiga",
      subs: "12M",
      league: "La Liga",
      videos: 87,
      sentimentPct: 82,
      sentimentDir: "up",
      latestTitle: "El Clasico - All Goals & Highlights",
      latestViews: "3.1M views",
      active: true,
    },
    {
      id: "bundesliga",
      initials: "B",
      name: "Bundesliga",
      handle: "@Bundesliga",
      subs: "8.4M",
      league: "Bundesliga",
      videos: 76,
      sentimentPct: 71,
      sentimentDir: "up",
      latestTitle: "Kane Hat-Trick vs Dortmund - All Angles",
      latestViews: "1.8M views",
      active: true,
    },
    {
      id: "seriea",
      initials: "SA",
      name: "Serie A Official",
      handle: "@SerieA",
      subs: "6.9M",
      league: "Serie A",
      videos: 64,
      sentimentPct: 55,
      sentimentDir: "down",
      latestTitle: "Napoli vs Inter - Full Match Recap",
      latestViews: "890K views",
      active: false,
    },
    {
      id: "athletic",
      initials: "TA",
      name: "The Athletic FC",
      handle: "@TheAthleticFC",
      subs: "1.8M",
      league: "Multi-League",
      videos: 54,
      sentimentPct: 76,
      sentimentDir: "up",
      latestTitle: "Why Arsenal Are Title Favorites - Deep Dive",
      latestViews: "720K views",
      active: true,
    },
    {
      id: "marca",
      initials: "M",
      name: "MARCA",
      handle: "@MARCATV",
      subs: "3.2M",
      league: "La Liga",
      videos: 45,
      sentimentPct: 79,
      sentimentDir: "up",
      latestTitle: "Vinicius Jr - Season Highlights 2024/25",
      latestViews: "2.1M views",
      active: true,
    },
    {
      id: "footballdaily",
      initials: "FD",
      name: "Football Daily",
      handle: "@FootballDaily",
      subs: "2.1M",
      league: "Multi-League",
      videos: 38,
      sentimentPct: 65,
      sentimentDir: "flat",
      latestTitle: "Transfer Window LIVE - Latest News & Rumors",
      latestViews: "430K views",
      active: true,
    },
  ]);

  const stats = useMemo(() => {
    const channelsTracked = rows.length;
    const activeCount = rows.filter((r) => r.active).length;
    const pausedCount = channelsTracked - activeCount;
    const totalVideos = rows.reduce((sum, r) => sum + r.videos, 0);
    const avgSent = Math.round(rows.reduce((sum, r) => sum + r.sentimentPct, 0) / channelsTracked);
    const apiUsed = 74; // mock
    const apiText = "7,420 / 10,000 daily";

    return {
      channelsTracked,
      activeCount,
      pausedCount,
      totalVideos,
      avgSent,
      apiUsed,
      apiText,
    };
  }, [rows]);

  const toggleActive = (id: string) => {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, active: !r.active } : r)));
  };

  return (
    <div className="min-h-screen w-full bg-black text-white">
      <div className="mx-auto max-w-6xl px-6 py-10">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-semibold tracking-tight">Channels</h1>
          <p className="mt-2 text-sm text-neutral-400">
            YouTube channels being monitored for sports content analysis
          </p>
        </div>

        {/* KPI Row */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <KpiCard
            title="Channels Tracked"
            value={`${stats.channelsTracked}`}
            trend="up"
            sub={`${stats.activeCount} active, ${stats.pausedCount} paused`}
            icon="📺"
          />
          <KpiCard
            title="Total Videos"
            value={`${stats.totalVideos}`}
            trend="down"
            sub="Last 30 days"
            icon="🎬"
          />
          <KpiCard
            title="Avg. Sentiment"
            value={`${stats.avgSent}%`}
            trend="down"
            sub="Across all channels"
            icon="📈"
          />
          <KpiCard
            title="API Quota Used"
            value={`${stats.apiUsed}%`}
            trend="up"
            sub={stats.apiText}
            icon="⚡"
          />
        </div>

        {/* Table */}
        <div className="mt-6 overflow-hidden rounded-2xl border border-neutral-800 bg-neutral-950/40 shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          {/* Header row */}
          <div className="grid grid-cols-12 gap-4 border-b border-neutral-800 px-5 py-3 text-xs uppercase tracking-wide text-neutral-500">
            <div className="col-span-4">Channel</div>
            <div className="col-span-2">League</div>
            <div className="col-span-1 text-right">Videos</div>
            <div className="col-span-1 text-right">Sentiment</div>
            <div className="col-span-3">Latest Video</div>
            <div className="col-span-1 text-right">Active</div>
          </div>

          <div className="divide-y divide-neutral-800">
            {rows.map((r) => (
              <ChannelRow key={r.id} row={r} onToggle={() => toggleActive(r.id)} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
