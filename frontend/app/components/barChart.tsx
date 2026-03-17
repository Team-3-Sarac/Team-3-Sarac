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

  if (loading || data.length === 0) {
    return (
      <div className="rounded-xl border border-neutral-800 bg-neutral-950 p-4">
        <div className="flex h-56 items-center justify-center text-neutral-500">
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-950 p-4">
      <div className="relative h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
            <XAxis 
              dataKey="label" 
              tick={{ fill: '#737373', fontSize: 12 }}
              axisLine={{ stroke: '#404040' }}
              tickLine={{ stroke: '#404040' }}
              dy={10}
            />
            <YAxis 
              tick={{ fill: '#737373', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill="#0ea5e9" />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
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
