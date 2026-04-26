"use client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { getTrendsHistory } from "../../api/backend";
import { useEffect, useState } from "react";

type TrendHistory = {
  week: string;
  transfers: number;
  injuries: number;
  tactics: number;
  controversy: number;
};

export default function LineChartComponent() {
  const [data, setData] = useState<TrendHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await getTrendsHistory();
        const history = res.history || [];
        const total = history.length;
        const formatted = history.map((w: any, i: number) => ({
          transfers: w.transfers ?? 0,
          injuries: w.injuries ?? 0,
          tactics: w.tactics ?? 0,
          controversy: w.controversy ?? 0,
          week: `${total - i} wk ago`,
        }));
        setData(formatted);
      } catch (err) {
        console.error("[LineChart] Failed to fetch trends history:", err);
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

  if (error) {
    return (
      <div className="flex h-56 items-center justify-center text-sm text-neutral-500">
        Failed to load trend history
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center text-sm text-neutral-500">
        No trend history available
      </div>
    );
  }

  const minWidth = Math.max(data.length * 80, 600);

  return (
    <>
      <style>{`
        .linechart-scroll::-webkit-scrollbar { height: 6px; }
        .linechart-scroll::-webkit-scrollbar-track { background: rgba(255,255,255,0.04); border-radius: 9999px; }
        .linechart-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.20); border-radius: 9999px; }
        .linechart-scroll::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.35); border-radius: 9999px; }
      `}</style>
      <div
        className="linechart-scroll w-full overflow-x-scroll overflow-y-hidden pb-2"
        style={{ scrollbarWidth: "thin", scrollbarColor: "rgba(255,255,255,0.20) rgba(255,255,255,0.04)" }}
      >
        <div style={{ width: minWidth, height: 224 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.04)"
                vertical={false}
              />
              <XAxis
                dataKey="week"
                tick={{ fill: "#525252", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                dy={8}
              />
              <YAxis
                tick={{ fill: "#525252", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0f0f0f",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: "8px",
                  fontSize: "12px",
                  boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
                }}
                labelStyle={{ color: "#737373", marginBottom: 4 }}
                cursor={{ stroke: "rgba(255,255,255,0.08)", strokeWidth: 1 }}
                itemSorter={(item) => {
                  const order: Record<string, number> = {
                    transfers: 0,
                    injuries: 1,
                    tactics: 2,
                    controversy: 3,
                  };
                  return order[item.dataKey as string] ?? 99;
                }}
              />
              <Line
                type="monotone"
                dataKey="transfers"
                stroke="#34d399"
                strokeWidth={2}
                dot={false}
                name="Transfers"
              />
              <Line
                type="monotone"
                dataKey="injuries"
                stroke="#f87171"
                strokeWidth={2}
                dot={false}
                name="Injuries"
              />
              <Line
                type="monotone"
                dataKey="tactics"
                stroke="#38bdf8"
                strokeWidth={2}
                dot={false}
                name="Tactics"
              />
              <Line
                type="monotone"
                dataKey="controversy"
                stroke="#fbbf24"
                strokeWidth={2}
                dot={false}
                name="Controversy"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  );
}
