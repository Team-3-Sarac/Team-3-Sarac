"use client";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from "recharts";
import { getLeagueStats } from "../../api/backend";
import { useEffect, useState } from "react";

const BAR_COLORS = ["#38bdf8", "#f87171", "#34d399", "#f97316", "#a78bfa", "#fbbf24"];

type LeagueData = {
  league: string;
  count: number;
  status: string;
};

function getLeagueShortName(league: string): string {
  const map: Record<string, string> = {
    "Premier League": "PL",
    "Champions League": "CL",
    "La Liga":        "La Liga",
    "Bundesliga":     "BL",
    "Serie A":        "Serie A",
    "Ligue 1":        "Ligue 1",
  };
  return map[league] || league.substring(0, 3);
}

export default function BarChartComponent() {
  const [data, setData] = useState<{ label: string; value: number; full: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await getLeagueStats();
        const leagues = res.leagues || [];
        setData(
          leagues
            .filter((l: LeagueData) => l.league && l.league !== "Unknown" && l.league !== "Unk")
            .map((l: LeagueData) => ({
              label: getLeagueShortName(l.league),
              value: l.count,
              full:  l.league,
            }))
        );
      } catch (err) {
        console.error("[BarChart] Failed to fetch league stats:", err);
        setError(true);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return <div className="relative h-56 animate-pulse rounded-xl bg-white/4" />;
  }

  if (error || data.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center text-sm text-neutral-500">
        {error ? "Failed to load league data" : "No league data available"}
      </div>
    );
  }

  return (
    <div className="relative h-56">
      <ResponsiveContainer width={"100%"} height={"100%"}>
        <BarChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
          <XAxis
            dataKey="label"
            tick={{ fill: "#737373", fontSize: 11 }}
            axisLine={{ stroke: "#404040" }}
            tickLine={{ stroke: "#404040" }}
          />
          <YAxis
            tick={{ fill: "#737373", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
