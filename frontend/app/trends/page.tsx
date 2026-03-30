"use client";
import { useEffect, useState } from "react";
import Skeleton from "../components/skeleton";
import Card from "../components/card";
import CardHeader from "../components/cardHeader";
import BarChart from "../components/barChart";
import LineChart from "../components/lineChart";
import Claims from "../components/claims";
import TopicRow from "../components/topicRow";
import SectionLabel from "../components/sectionLabel";
import EmptyState from "../components/emptyState";
import { getTrends, getLeagueStats, getNarratives } from "../../api/backend";

/* ---------------- Types ---------------- */

type Trend = {
  id: string;
  narrative_id: string;
  league: string | null;
  time_window: string;
  mention_count: number;
  trending_direction: string;
  score: number;
  created_at: string;
};

type Narrative = {
  id: string;
  title: string;
  league: string | null;
  claims_ids: string[];
  created_at: string;
};

type League = {
  league: string;
  count: number;
  status: string;
};

/* ---------------- Helpers ---------------- */

function getChangeDir(direction: string): "up" | "down" | "flat" {
  if (direction === "up") return "up";
  if (direction === "down") return "down";
  return "flat";
}

function formatChange(direction: string, mentionCount: number): string {
  if (direction === "up") return `+${Math.min(Math.round(mentionCount / 10), 50)}%`;
  if (direction === "down") return `-${Math.min(Math.round(mentionCount / 10), 20)}%`;
  return "0%";
}

function getTopicLeagues(trend: Trend, leagues: League[]): string[] {
  const result: string[] = [];
  if (trend.league) {
    result.push(trend.league.length > 12 ? trend.league.substring(0, 12) + "…" : trend.league);
  }
  if (leagues.length > 0 && leagues[0]?.league !== trend.league) {
    result.push(leagues[0]?.league?.substring(0, 12) + "…" || "Multi");
  }
  return result.length > 0 ? result : ["Multi-League"];
}

/* ---------------- Primitives (mirrors Dashboard) ---------------- */

function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="divide-y divide-white/4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="grid grid-cols-12 gap-4 px-6 py-4">
          <div className="col-span-6 flex items-center gap-3">
            <Skeleton className="h-3.5 w-3.5 rounded" />
            <Skeleton className="h-3.5 w-40" />
          </div>
          <div className="col-span-2 flex justify-end"><Skeleton className="h-3.5 w-10" /></div>
          <div className="col-span-2 flex justify-end"><Skeleton className="h-3.5 w-12" /></div>
          <div className="col-span-2 flex justify-end"><Skeleton className="h-5 w-16 rounded-md" /></div>
        </div>
      ))}
    </div>
  );
}

/* ================================================================
   PAGE
================================================================ */

export default function TrendsPage() {
  const [trends, setTrends] = useState<Trend[]>([]);
  const [narratives, setNarratives] = useState<Narrative[]>([]);
  const [leagues, setLeagues] = useState<League[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        const [trendsRes, leagueRes, narrativesRes] = await Promise.all([
          getTrends(),
          getLeagueStats(),
          getNarratives(),
        ]);
        setTrends(trendsRes.trends || []);
        setLeagues(leagueRes.leagues || []);
        setNarratives(narrativesRes.narratives || []);
      } catch (err) {
        console.error("Failed to fetch trends data:", err);
        setError(true);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

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
          <SectionLabel>Analysis</SectionLabel>
          <h1
            className="mt-2 text-[clamp(2rem,4vw,2.8rem)] font-black leading-tight tracking-[-0.02em]"
            style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
          >
            Trends
          </h1>
          <p className="mt-2 text-sm text-neutral-500">
            Discover trending topics and narratives across European soccer leagues
          </p>
        </div>

        {/* ── Accent line ── */}
        <div className="mb-6 h-px w-full bg-linear-to-r from-transparent via-teal-500/30 to-transparent" />

        {/* ── Top charts ── */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader
              title="Content Volume by League"
              subtitle="Videos analyzed per league this month"
            />
            <div className="px-6 pb-6 pt-4">
              <BarChart />
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Narrative Trends"
              subtitle="Topic frequency over the past 6 weeks"
              legendItems={[
                { color: "bg-emerald-400", label: "Transfers" },
                { color: "bg-red-400",     label: "Injuries" },
                { color: "bg-sky-400",     label: "Tactics" },
                { color: "bg-amber-400",   label: "Controversy" },
              ]}
            />
            <div className="px-6 pb-6 pt-4">
              <LineChart />
            </div>
          </Card>
        </div>

        {/* ── Claims ── */}
        <div className="mt-6">
          <Claims />
        </div>

        {/* ── Trending Topics table ── */}
        <div className="mt-6">
          <Card>
            <CardHeader
              title="Trending Topics"
              subtitle="Most discussed narratives across YouTube soccer content"
            />

            {/* Table header */}
            <div className="grid grid-cols-12 gap-4 border-b border-white/6 px-6 py-3">
              <div className="col-span-6 text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Topic</div>
              <div className="col-span-2 text-right text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Mentions</div>
              <div className="col-span-2 text-right text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Change</div>
              <div className="col-span-2 text-right text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Leagues</div>
            </div>

            <div className="divide-y divide-white/4">
              {loading ? (
                <TableSkeleton />
              ) : error || trends.length === 0 ? (
                <EmptyState message={error ? "Failed to load trends" : "No trends available"} />
              ) : (
                trends.map((trend) => (
                  <TopicRow
                    key={trend.id}
                    hot={trend.trending_direction === "up" && trend.score >= 0.75}
                    topic={
                      narratives.find((n) => n.id === trend.narrative_id)?.title ||
                      trend.league ||
                      "General Topic"
                    }
                    mentions={trend.mention_count.toString()}
                    change={formatChange(trend.trending_direction, trend.mention_count)}
                    changeDir={getChangeDir(trend.trending_direction)}
                    leagues={getTopicLeagues(trend, leagues)}
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
