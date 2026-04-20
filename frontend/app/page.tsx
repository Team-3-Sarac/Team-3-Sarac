"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getDashboardKPIs } from "./../api/backend";
import { TrendingUp, Video, Activity, Users, Shield, Radio, ChevronRight, Eye, Zap, BarChart2 } from "lucide-react";

/* ---------------- Types ---------------- */

type KPIs = {
  videos_analyzed: number;
  trending_topics: number;
  avg_sentiment: number;
  channels_tracked: number;
  videos_this_week: number;
  topics_since_yesterday: number;
};

/* ---------------- Helpers ---------------- */

function formatNumber(num: number): string {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toLocaleString();
}

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

/* ---------------- Constants ---------------- */

const FEATURES = [
  {
    icon: <TrendingUp className="h-5 w-5" />,
    label: "Trend Analysis",
    desc: "Track which topics, leagues, and events are gaining traction across YouTube, updated in real time as new content is published.",
  },
  {
    icon: <Shield className="h-5 w-5" />,
    label: "Creator Risk Scoring",
    desc: "Automatically score channels based on misinformation, toxicity, violence, and other harmful content patterns over time.",
  },
  {
    icon: <Activity className="h-5 w-5" />,
    label: "Sentiment Monitoring",
    desc: "Measure fan mood across channels, leagues, and matches using YouTube videos and comments.",
  },
  {
    icon: <Eye className="h-5 w-5" />,
    label: "Claim Detection",
    desc: "Monitor and analyze trending claims using confidence scoring, mention volume, and sentiment signals.",
  },
  {
    icon: <Radio className="h-5 w-5" />,
    label: "Channel Insights",
    desc: "Explore individual channel profiles with sentiment, league associations, video count, and recent uploads.",
  },
  {
    icon: <BarChart2 className="h-5 w-5" />,
    label: "Cross-League Benchmarking",
    desc: "Compare video volume, sentiment, and engagement across the Premier League, La Liga, Bundesliga, Serie A, and Ligue 1.",
  },
];

const LEAGUES = ["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"];

/* Page */

export default function LandingPage() {
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [kpisError, setKpisError] = useState(false);

  const animatedVideos    = useCountUp(kpis?.videos_analyzed   ?? null);
  const animatedTopics    = useCountUp(kpis?.trending_topics   ?? null);
  const animatedSentiment = useCountUp(kpis ? kpis.avg_sentiment * 100 : null);
  const animatedChannels  = useCountUp(kpis?.channels_tracked  ?? null);

  useEffect(() => {
    getDashboardKPIs()
      .then(setKpis)
      .catch((err) => {
        console.error("[Landing] Failed to fetch KPIs:", err);
        setKpisError(true);
      });
  }, []);

  // Derived display values — always respect error state
  const kpiStats = [
    {
      icon: <Video className="h-3.5 w-3.5" />,
      title: "Videos Analyzed",
      value: kpisError ? "—" : kpis ? formatNumber(animatedVideos) : "—",
      sub: kpisError ? "Failed to load" : kpis ? `+${kpis.videos_this_week} this week` : "Loading…",
    },
    {
      icon: <TrendingUp className="h-3.5 w-3.5" />,
      title: "Trending Topics",
      value: kpisError ? "—" : kpis ? formatNumber(animatedTopics) : "—",
      sub: kpisError ? "Failed to load" : kpis ? `+${kpis.topics_since_yesterday} since yesterday` : "Loading…",
    },
    {
      icon: <Activity className="h-3.5 w-3.5" />,
      title: "Avg. Sentiment",
      value: kpisError ? "—" : kpis ? `${Math.round(animatedSentiment)}%` : "—",
      sub: kpisError ? "Failed to load" : kpis
        ? kpis.avg_sentiment >= 0.6 ? "Positive overall"
        : kpis.avg_sentiment >= 0.4 ? "Neutral overall"
        : "Negative overall"
        : "Loading…",
    },
    {
      icon: <Users className="h-3.5 w-3.5" />,
      title: "Channels Tracked",
      value: kpisError ? "—" : kpis ? formatNumber(animatedChannels) : "—",
      sub: kpisError ? "Failed to load" : `${LEAGUES.length} leagues`,
    },
  ];

  const isLoading = !kpisError && kpis === null;

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-[#080808] text-white">

      {/* ── HERO ── */}
      <section className="relative flex min-h-[92vh] flex-col items-center justify-center overflow-hidden px-6 text-center">

        {/* Grid background */}
        <div className="pointer-events-none absolute inset-0 opacity-[0.06]">
          <div
            className="h-full w-full"
            style={{
              backgroundImage: `
                radial-gradient(circle at center, white 1px, transparent 1px),
                linear-gradient(to right, white 1px, transparent 1px),
                linear-gradient(to bottom, white 1px, transparent 1px)
              `,
              backgroundSize: "120px 120px, 120px 120px, 120px 120px",
            }}
          />
        </div>

        {/* Live pill */}
        <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/4 px-4 py-1.5 text-xs text-neutral-400 backdrop-blur-sm">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-teal-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-teal-500 shadow-[0_0_8px_#22d3ee]" />
          </span>
          Live intelligence ·{" "}
          <span className="text-white font-medium">
            {kpisError ? "—" : kpis ? formatNumber(animatedVideos) : "—"}
          </span>{" "}
          videos monitored
        </div>

        {/* Headline */}
        <h1
          className="mx-auto max-w-4xl text-balance text-[clamp(2.6rem,6vw,5rem)] font-black leading-[1.05] tracking-[-0.03em]"
          style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
        >
          Soccer Intelligence,{" "}
          Analyzed from YouTube
        </h1>

        {/* Sub */}
        <p className="mx-auto mt-6 max-w-xl text-balance text-[15px] leading-relaxed text-neutral-400">
          MatchIQ analyzes claims, narratives, trends, and creator risk across
          YouTube, highlighting patterns in soccer content across top European leagues.
        </p>

        {/* CTAs */}
        <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/dashboard"
            className="group inline-flex items-center gap-2 rounded-lg bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-teal-500"
          >
            Open Dashboard
            <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
          <Link
            href="/trends"
            className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/4 px-5 py-2.5 text-sm font-medium text-neutral-300 transition-all hover:border-white/20 hover:bg-white/7 hover:text-white"
          >
            Explore Trends
          </Link>
        </div>

        {/* Scroll hint */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1.5 text-[11px] text-neutral-600">
          <span>Scroll to explore</span>
          <div className="h-5 w-px bg-linear-to-b from-neutral-600 to-transparent" />
        </div>
      </section>

      {/* STATS + LEAGUES */}
      <section className="border-y border-white/6 bg-white/2 py-10">
        <div className="mx-auto max-w-6xl px-6">

          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {kpiStats.map((stat) => (
              <div
                key={stat.title}
                className="flex flex-col gap-3 rounded-xl border border-white/[0.07] bg-[#0f0f0f] p-6"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold uppercase tracking-widest text-neutral-500">
                    {stat.title}
                  </span>
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-white/[0.07] bg-white/4 text-neutral-400">
                    {stat.icon}
                  </div>
                </div>
                {isLoading ? (
                  <>
                    <div className="h-8 w-24 animate-pulse rounded bg-white/4" />
                    <div className="h-3 w-32 animate-pulse rounded bg-white/4" />
                  </>
                ) : (
                  <>
                    <div
                      className="text-[2rem] font-black leading-none tracking-tight text-white"
                      style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
                    >
                      {stat.value}
                    </div>
                    <div className="text-xs text-emerald-400">
                      {stat.sub}
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>

          {/* Leagues strip */}
          <div className="mt-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
            <span className="text-[10px] font-semibold uppercase tracking-widest text-neutral-600">
              Covering
            </span>
            <div className="h-3 w-px bg-white/10" />
            {LEAGUES.map((league, i) => (
              <span key={i} className="text-[13px] text-neutral-500">
                {league}
              </span>
            ))}
          </div>

        </div>
      </section>

      {/* FEATURES */}
      <section className="border-t border-white/6 bg-white/2 px-6 py-20">
        <div className="mx-auto max-w-6xl">

          <div className="mb-12 flex flex-col items-start gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-widest text-teal-400">What It Does</span>
              <h2
                className="mt-2 text-[clamp(1.8rem,3.5vw,2.8rem)] font-black tracking-tight leading-tight"
                style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
              >
                Everything you need to<br />track the conversation
              </h2>
            </div>
            <p className="max-w-sm text-sm text-neutral-500 leading-relaxed md:text-right">
              From real-time sentiment to AI-generated weekly digests,
              MatchIQ keeps you ahead of the narrative.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-px bg-white/5 border border-white/5 rounded-xl overflow-hidden sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f, i) => (
              <div
                key={i}
                className="group flex flex-col gap-4 bg-[#080808] p-7 transition-all hover:bg-white/5 hover:shadow-[0_0_20px_rgba(34,211,238,0.1)]"
              >
                <div className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-white/8 bg-white/4 text-neutral-400 transition-colors group-hover:border-white/15 group-hover:bg-white/7 group-hover:text-white">
                  {f.icon}
                </div>
                <div>
                  <div className="text-sm font-semibold text-white">{f.label}</div>
                  <div className="mt-1.5 text-sm leading-relaxed text-neutral-500">{f.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12">
            <span className="text-[11px] font-semibold uppercase tracking-widest text-teal-400">How It Works</span>
            <h2
              className="mt-2 text-[clamp(1.8rem,3.5vw,2.8rem)] font-black tracking-tight"
              style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
            >
              From YouTube to insight<br />in three steps
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {[
              {
                step: "01",
                icon: <Radio className="h-5 w-5 text-neutral-400" />,
                title: "Ingest & Index",
                desc: "MatchIQ continuously pulls video metadata, transcripts, and engagement signals from tracked YouTube channels across five major European leagues, building a structured index of soccer content.",
              },
              {
                step: "02",
                icon: <Zap className="h-5 w-5 text-neutral-400" />,
                title: "Analyze & Score",
                desc: "LLM pipelines process every transcript to extract claims, detect emerging narratives, and measure fan sentiment. Then, they score each creator for risk signals like misinformation, toxicity, and harmful content patterns.",
              },
              {
                step: "03",
                icon: <BarChart2 className="h-5 w-5 text-neutral-400" />,
                title: "Surface & Act",
                desc: "Insights are surfaced across dashboards, trend charts, and channel profiles, presenting a clear view of what's being said, who's saying it, and how narratives are shifting across leagues.",
              },
            ].map((s) => (
              <div key={s.step} className="relative rounded-xl border border-white/7 bg-white/2 p-7">
                <div
                  className="absolute right-6 top-6 text-5xl font-black text-white/4 leading-none select-none"
                  style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
                >
                  {s.step}
                </div>
                <div className="mb-4 inline-flex h-9 w-9 items-center justify-center rounded-lg border border-white/8 bg-white/4">
                  {s.icon}
                </div>
                <div className="text-sm font-semibold text-white">{s.title}</div>
                <div className="mt-2 text-sm leading-relaxed text-neutral-500">{s.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 pb-24">
        <div className="mx-auto max-w-6xl">
          <div className="relative overflow-hidden rounded-2xl border border-white/7 bg-white/2 px-10 py-14 text-center">
            <div className="relative">
              <h2
                className="text-[clamp(1.6rem,3vw,2.4rem)] font-black tracking-tight"
                style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
              >
                Ready to explore?
              </h2>
              <p className="mx-auto mt-3 max-w-md text-sm text-neutral-400">
                Jump into the dashboard to see live sentiment trends,
                trending match content, and AI-generated intelligence.
              </p>
              <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
                <Link
                  href="/dashboard"
                  className="group inline-flex items-center gap-2 rounded-lg bg-teal-600 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-teal-500"
                >
                  Open Dashboard
                  <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </Link>
                <Link
                  href="/channels"
                  className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-6 py-3 text-sm font-medium text-neutral-300 transition-all hover:border-white/20 hover:text-white"
                >
                  Browse Channels
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-white/6 px-6 py-8">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <span
            className="text-sm font-semibold text-white/60"
            style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
          >
            Match<span className="text-teal-400">IQ</span>
          </span>
          <span className="text-xs text-neutral-600">
            YouTube Soccer Intelligence Platform
          </span>
        </div>
      </footer>

    </div>
  );
}