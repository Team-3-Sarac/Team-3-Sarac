"use client";
import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";
import { getSentimentHistory } from "../../api/backend";
import { useEffect, useState } from "react";

type SentimentData = {
  week: string;
  positive: number;
  negative: number;
};

export default function SentimentChart() {
  const [data, setData] = useState<SentimentData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await getSentimentHistory();
        // Format week labels to day names
        const formatted = (res.weeks || []).map((w: SentimentData, i: number) => ({
          ...w,
          week: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][i % 7] || w.week,
        }));
        setData(formatted);
      } catch (err) {
        console.error("Failed to fetch sentiment history:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading || data.length === 0) {
    return (
      <div className="relative h-64 w-full overflow-hidden rounded-xl border border-neutral-800 bg-neutral-950">
        <div className="flex h-full items-center justify-center text-neutral-500">
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-64 w-full overflow-hidden rounded-xl border border-neutral-800 bg-neutral-950">
      {/* grid lines */}
      <div className="absolute inset-0 opacity-60">
        <div className="h-full w-full bg-[linear-gradient(to_right,rgba(255,255,255,0.06)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.06)_1px,transparent_1px)] bg-[size:56px_56px]" />
      </div>

      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 30 }}>
          <defs>
            <linearGradient id="colorPositive" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#38bdf8" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="colorNegative" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <XAxis 
            dataKey="week" 
            tick={{ fill: '#737373', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            dy={10}
          />
          <YAxis 
            tick={{ fill: '#737373', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            domain={[0, 100]}
            tickFormatter={(value) => `${value}%`}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#171717', 
              border: '1px solid #404040',
              borderRadius: '8px',
              fontSize: '12px'
            }}
            labelStyle={{ color: '#a3a3a3' }}
            formatter={(value) => [`${Number(value).toFixed(1)}%`, '']}
          />
          <Area 
            type="monotone" 
            dataKey="positive" 
            stroke="#38bdf8" 
            strokeWidth={2.5}
            fillOpacity={1}
            fill="url(#colorPositive)"
            name="Positive"
          />
          <Area 
            type="monotone" 
            dataKey="negative" 
            stroke="#ef4444" 
            strokeWidth={2.5}
            fillOpacity={1}
            fill="url(#colorNegative)"
            name="Negative"
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* y labels overlay */}
      <div className="absolute left-3 top-3 flex h-[calc(100%-44px)] flex-col justify-between text-[11px] text-neutral-500 pointer-events-none">
        <span>100%</span>
        <span>75%</span>
        <span>50%</span>
        <span>25%</span>
        <span>0%</span>
      </div>
    </div>
  );
}
