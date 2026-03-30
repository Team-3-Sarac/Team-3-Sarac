"use client";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  CartesianGrid,
} from "recharts";

type SentimentData = {
  week: string;
  positive: number;
  negative: number;
};

export default function SentimentChart({ data }: { data: SentimentData[] }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center text-sm text-neutral-600">
        No sentiment data available
      </div>
    );
  }

  return (
    <div className="h-full w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
          <defs>
            <linearGradient id="colorPositive" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorNegative" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
          </defs>

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
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
            ticks={[0, 25, 50, 75, 100]}
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
            formatter={(value, name) => [
              `${Number(value).toFixed(1)}%`,
              name === "positive" ? "Positive" : "Negative",
            ]}
            cursor={{ stroke: "rgba(255,255,255,0.08)", strokeWidth: 1 }}
          />

          <Area
            type="monotone"
            dataKey="positive"
            stroke="#38bdf8"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorPositive)"
            name="positive"
          />
          <Area
            type="monotone"
            dataKey="negative"
            stroke="#ef4444"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorNegative)"
            name="negative"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}