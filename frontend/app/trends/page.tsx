"use client";
import { useEffect, useState } from "react";
import Card from "../components/card";
import CardHeader from "../components/cardHeader";
import LegendDot from "../components/legendDot";
import BarChart from "../components/barChart";
import LineChart from "../components/lineChart";
import TopicRow from "../components/topicRow";
import Claims from "../components/claims";
import { getTrends, getLeagueStats, getNarratives, getClaims } from "../../api/backend";

import { Flame, TrendingUp, TrendingDown } from "lucide-react";

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

export default function TrendsPage() {
  const [trends, setTrends] = useState<Trend[]>([]);
  const [narratives, setNarratives] = useState<Narrative[]>([]);
  const [leagues, setLeagues] = useState<League[]>([]);
  const [loading, setLoading] = useState(true);

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
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const getChangeDir = (direction: string): "up" | "down" | "flat" => {
    if (direction === "up") return "up";
    if (direction === "down") return "down";
    return "flat";
  };

  const formatChange = (direction: string, mentionCount: number): string => {
    if (direction === "up") return `+${Math.min(Math.round(mentionCount / 10), 50)}%`;
    if (direction === "down") return `-${Math.min(Math.round(mentionCount / 10), 20)}%`;
    return "0%";
  };

  const getTopicLeagues = (trend: Trend): string[] => {
    const result: string[] = [];
    if (trend.league) result.push(trend.league.length > 12 ? trend.league.substring(0, 12) + "…" : trend.league);
    if (leagues.length > 0 && leagues[0]?.league !== trend.league) {
      result.push(leagues[0]?.league?.substring(0, 12) + "…" || "Multi");
    }
    return result.length > 0 ? result : ["Multi-League"];
  };

  return (
    <div className="min-h-screen w-full bg-black text-white">
      <div className="mx-auto max-w-6xl px-6 py-10">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-semibold tracking-tight">Trend Detection</h1>
          <p className="mt-2 text-sm text-neutral-400">
            Discover trending topics and narratives across European soccer leagues
          </p>
        </div>

        {/* Top charts */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader
              title="Content Volume by League"
              subtitle="Videos analyzed per league this month"
            />
            <div className="p-5">
              <BarChart />
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Narrative Trends"
              subtitle="Topic frequency over the past 6 weeks"
            />
            <div className="p-5">
              <LineChart />
              <div className="mt-4 flex flex-wrap gap-4 text-xs text-neutral-400">
                <LegendDot color="bg-emerald-400" label="Transfers" />
                <LegendDot color="bg-red-400" label="Injuries" />
                <LegendDot color="bg-sky-400" label="Tactics" />
                <LegendDot color="bg-amber-400" label="Controversy" />
              </div>
            </div>
          </Card>
        </div>

        {/* Claims */}
        <div className="mt-6">
          <Claims />
        </div>

        {/* Table */}
        <div className="mt-6">
          <Card>
            <CardHeader
              title="Trending Topics"
              subtitle="Most discussed narratives across YouTube soccer content"
            />

            <div className="overflow-hidden">
              {/* table header */}
              <div className="grid grid-cols-12 gap-4 border-b border-neutral-800 px-5 py-3 text-xs uppercase tracking-wide text-neutral-500">
                <div className="col-span-6">Topic</div>
                <div className="col-span-2 text-right">Mentions</div>
                <div className="col-span-2 text-right">Change</div>
                <div className="col-span-2 text-right">Leagues</div>
              </div>

              <div className="divide-y divide-neutral-800">
                {loading || trends.length === 0 ? (
                  <div className="px-5 py-10 text-center text-sm text-neutral-500">No trends available</div>
                ) : (
                  trends.map((trend) => (
                    <TopicRow
                      key={trend.id}
                      hot={trend.trending_direction === "up" && trend.mention_count > 5}
                      topic={trend.league || "General Topic"}
                      mentions={trend.mention_count.toString()}
                      change={formatChange(trend.trending_direction, trend.mention_count)}
                      changeDir={getChangeDir(trend.trending_direction)}
                      leagues={getTopicLeagues(trend)}
                    />
                  ))
                )}
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
