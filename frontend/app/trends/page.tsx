"use client";

import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";
import "@/styles/trends.css";

// ─── Data ─────────────────────────────────────────────────────────────────────

const volumeData = [
  { league: "PL", videos: 430 },
  { league: "La Liga", videos: 290 },
  { league: "BL", videos: 195 },
  { league: "Serie A", videos: 180 },
  { league: "Ligue 1", videos: 168 },
];

const narrativeData = [
  { week: "W1", Transfers: 45, Injuries: 13, Tactics: 31, Controversy: 17 },
  { week: "W2", Transfers: 38, Injuries: 15, Tactics: 29, Controversy: 22 },
  { week: "W3", Transfers: 55, Injuries: 10, Tactics: 27, Controversy: 30 },
  { week: "W4", Transfers: 32, Injuries: 22, Tactics: 36, Controversy: 20 },
  { week: "W5", Transfers: 28, Injuries: 18, Tactics: 40, Controversy: 24 },
  { week: "W6", Transfers: 34, Injuries: 14, Tactics: 45, Controversy: 28 },
];

const trendingTopics = [
  {
    icon: "↗",
    topic: "Transfer Window Speculation",
    mentions: 342,
    change: 28,
    leagues: ["Premier", "La Liga"],
  },
  {
    icon: "🔴",
    topic: "Injury Crisis Reports",
    mentions: 218,
    change: -5,
    leagues: ["Bundesliga", "Serie A"],
  },
  {
    icon: "⚡",
    topic: "Tactical Evolutions",
    mentions: 197,
    change: 14,
    leagues: ["Premier", "Ligue 1"],
  },
  {
    icon: "🔥",
    topic: "Referee Controversies",
    mentions: 165,
    change: 41,
    leagues: ["La Liga", "Serie A"],
  },
  {
    icon: "⭐",
    topic: "Young Talent Spotlights",
    mentions: 143,
    change: 9,
    leagues: ["Bundesliga", "Premier"],
  },
];

const lineConfig: Record<string, string> = {
  Transfers: "#10b981",
  Injuries: "#ef4444",
  Tactics: "#3b82f6",
  Controversy: "#f59e0b",
};

// ─── Sub-components ────────────────────────────────────────────────────────────

function StatBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat-badge">
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

const CustomBarTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="tooltip">
      <p className="tooltip-label">{label}</p>
      <p className="tooltip-sub">{payload[0].value} videos</p>
    </div>
  );
};



// ─── Main Page ─────────────────────────────────────────────────────────────────

export default function TrendDetectionPage() {
  const [activeLines, setActiveLines] = useState<string[]>(Object.keys(lineConfig));

  const toggleLine = (key: string) => {
    setActiveLines((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  return (
    <div className="trends-page">
      {/* Header */}
      <div className="trends-header">
        <h1>Trend Detection</h1>
        <p>Discover trending topics and narratives across European soccer leagues</p>
      </div>

      {/* Stats Row */}
      <div className="stats-row">
        <StatBadge label="Videos Analyzed" value="1,260" />
        <StatBadge label="Trending Topics" value="24" />
        <StatBadge label="Avg. Weekly Mentions" value="893" />
        <StatBadge label="Leagues Tracked" value="5" />
      </div>

      {/* Charts Grid */}
      <div className="charts-grid">
        {/* Bar Chart */}
        <div className="card">
          <div className="card-header">
            <h2>Content Volume by League</h2>
            <p>Videos analyzed per league this month</p>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={volumeData} barCategoryGap="35%">
              <CartesianGrid vertical={false} strokeDasharray="4 4" stroke="var(--border)" />
              <XAxis
                dataKey="league"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "var(--text-muted)", fontSize: 12, fontWeight: 500 }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                tickCount={5}
              />
              <Tooltip content={<CustomBarTooltip />} cursor={{ fill: "var(--bg-card)" }} />
              <Bar dataKey="videos" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Line Chart */}
        <div className="card">
          <div className="card-header">
            <h2>Narrative Trends</h2>
            <p>Topic frequency over the past 6 weeks</p>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={narrativeData}>
              <CartesianGrid strokeDasharray="4 4" stroke="var(--border)" />
              <XAxis
                dataKey="week"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "var(--text-muted)", fontSize: 12 }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                tickCount={5}
              />
            
              {Object.entries(lineConfig).map(([key, color]) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={color}
                  strokeWidth={2.5}
                  dot={false}
                  strokeOpacity={activeLines.includes(key) ? 1 : 0.12}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>

          {/* Legend */}
          <div className="legend">
            {Object.entries(lineConfig).map(([key, color]) => (
              <button
                key={key}
                onClick={() => toggleLine(key)}
                className={`legend-btn${!activeLines.includes(key) ? " inactive" : ""}`}
              >
                <span className="legend-dot" style={{ background: color }} />
                {key}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Trending Topics Table */}
      <div className="table-card">
        <div className="table-header">
          <h2>Trending Topics</h2>
          <p>Most discussed narratives across YouTube soccer content</p>
        </div>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Topic</th>
                <th>Mentions</th>
                <th>Change</th>
                <th>Leagues</th>
              </tr>
            </thead>
            <tbody>
              {trendingTopics.map((item, i) => (
                <tr key={i}>
                  <td>
                    <div className="topic-cell">
                      <span className="topic-icon">{item.icon}</span>
                      <span className="topic-name">{item.topic}</span>
                    </div>
                  </td>
                  <td>
                    <span className="mentions">{item.mentions.toLocaleString()}</span>
                  </td>
                  <td>
                    <span className={`change-badge ${item.change >= 0 ? "positive" : "negative"}`}>
                      {item.change >= 0 ? "↑" : "↓"} {Math.abs(item.change)}%
                    </span>
                  </td>
                  <td>
                    <div className="league-tags">
                      {item.leagues.map((l) => (
                        <span key={l} className="league-tag">{l}</span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}