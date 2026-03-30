"use client";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from "recharts";
import { getLeagueStats } from "../../api/backend";
import { useEffect, useState } from "react";

type LeagueData = {
  league: string;
  count: number;
  status: string;
};

export default function BarChartComponent() {
  const [data, setData] = useState<LeagueData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await getLeagueStats();
        const leagues = res.leagues || [];
        
        // Format for Recharts with short labels
        const formatted = leagues.map((l: LeagueData) => ({
          label: getLeagueShortName(l.league),
          value: l.count,
          full: l.league,
        }));
        
        setData(formatted);
      } catch (err) {
        console.error("Failed to fetch league stats:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return <div className="relative h-56 animate-pulse rounded-xl bg-white/4" />;
  }

  if (data.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center text-sm text-neutral-500">
        No league data available
      </div>
    );
  }
}

function getLeagueShortName(league: string): string {
  const map: Record<string, string> = {
    "Premier League": "PL",
    "La Liga": "La Liga",
    "Bundesliga": "BL",
    "Serie A": "Serie A",
    "Ligue 1": "Ligue 1",
  };
  return map[league] || league.substring(0, 3);
}
