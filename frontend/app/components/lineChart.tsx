"use client";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Legend } from "recharts";
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

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await getTrendsHistory();
        setData(res.history || []);
      } catch (err) {
        console.error("Failed to fetch trends history:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading || data.length === 0) {
    return (
      <div className="relative h-64 overflow-hidden rounded-xl border border-neutral-800 bg-neutral-950 p-4">
        <div className="flex h-full items-center justify-center text-neutral-500">
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-64 overflow-hidden rounded-xl border border-neutral-800 bg-neutral-950 p-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
          <XAxis 
            dataKey="week" 
            tick={{ fill: '#737373', fontSize: 11 }}
            axisLine={{ stroke: '#404040' }}
            tickLine={{ stroke: '#404040' }}
          />
          <YAxis 
            tick={{ fill: '#737373', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
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
  );
}
