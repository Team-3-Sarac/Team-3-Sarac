"use client";

import { useState } from "react";
import "@/styles/channels.css";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Channel {
  initials: string;
  name: string;
  handle: string;
  subscribers: string;
  league: string;
  videos: number;
  sentiment: number;
  sentimentTrend: "up" | "down" | "neutral";
  latestVideo: string;
  views: string;
  active: boolean;
}

// ─── Data ─────────────────────────────────────────────────────────────────────

const initialChannels: Channel[] = [
  {
    initials: "SS",
    name: "Sky Sports Football",
    handle: "@SkySportsFootball",
    subscribers: "7.2M",
    league: "Premier League",
    videos: 142,
    sentiment: 74,
    sentimentTrend: "up",
    latestVideo: "Arsenal vs Man City - Extended Hig...",
    views: "2.4M views",
    active: true,
  },
  {
    initials: "E",
    name: "ESPNFC",
    handle: "@ESPNFC",
    subscribers: "5.1M",
    league: "Multi-League",
    videos: 98,
    sentiment: 68,
    sentimentTrend: "neutral",
    latestVideo: "Title Race Power Rankings - Februa...",
    views: "1.1M views",
    active: true,
  },
  {
    initials: "LO",
    name: "LaLiga Official",
    handle: "@LaLiga",
    subscribers: "12M",
    league: "La Liga",
    videos: 87,
    sentiment: 82,
    sentimentTrend: "up",
    latestVideo: "El Clasico - All Goals & Highlights",
    views: "3.1M views",
    active: true,
  },
  {
    initials: "B",
    name: "Bundesliga",
    handle: "@Bundesliga",
    subscribers: "8.4M",
    league: "Bundesliga",
    videos: 76,
    sentiment: 71,
    sentimentTrend: "up",
    latestVideo: "Kane Hat-Trick vs Dortmund - All A...",
    views: "1.8M views",
    active: true,
  },
  {
    initials: "SA",
    name: "Serie A Official",
    handle: "@SerieA",
    subscribers: "6.9M",
    league: "Serie A",
    videos: 64,
    sentiment: 55,
    sentimentTrend: "down",
    latestVideo: "Napoli vs Inter - Full Match Recap",
    views: "890K views",
    active: false,
  },
  {
    initials: "TA",
    name: "The Athletic FC",
    handle: "@TheAthleticFC",
    subscribers: "1.8M",
    league: "Multi-League",
    videos: 54,
    sentiment: 76,
    sentimentTrend: "up",
    latestVideo: "Why Arsenal Are Title Favorites - D...",
    views: "720K views",
    active: true,
  },
  {
    initials: "M",
    name: "MARCA",
    handle: "@MARCAtv",
    subscribers: "3.2M",
    league: "La Liga",
    videos: 45,
    sentiment: 79,
    sentimentTrend: "up",
    latestVideo: "Vinicius Jr - Season Highlights 202...",
    views: "2.1M views",
    active: true,
  },
  {
    initials: "FD",
    name: "Football Daily",
    handle: "@FootballDaily",
    subscribers: "2.1M",
    league: "Multi-League",
    videos: 38,
    sentiment: 65,
    sentimentTrend: "neutral",
    latestVideo: "Transfer Window LIVE - Latest New...",
    views: "430K views",
    active: true,
  },
];

// ─── Toggle Component ─────────────────────────────────────────────────────────

function Toggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label className="toggle">
      <input type="checkbox" checked={checked} onChange={onChange} />
      <span className="toggle-track" />
      <span className="toggle-thumb" />
    </label>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────────

export default function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>(initialChannels);

  const toggleChannel = (index: number) => {
    setChannels((prev) =>
      prev.map((ch, i) => (i === index ? { ...ch, active: !ch.active } : ch))
    );
  };

  const activeCount = channels.filter((c) => c.active).length;
  const totalVideos = channels.reduce((sum, c) => sum + c.videos, 0);
  const avgSentiment = Math.round(
    channels.reduce((sum, c) => sum + c.sentiment, 0) / channels.length
  );

  const sentimentClass = (trend: Channel["sentimentTrend"]) => {
    if (trend === "up") return "sentiment-up";
    if (trend === "down") return "sentiment-down";
    return "sentiment-neutral";
  };

  const sentimentArrow = (trend: Channel["sentimentTrend"]) => {
    if (trend === "up") return "↑";
    if (trend === "down") return "↓";
    return "—";
  };

  return (
    <div className="channels-page">
      {/* Header */}
      <div className="channels-header">
        <h1>Channels</h1>
        <p>YouTube channels being monitored for sports content analysis</p>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-tile">
          <div className="stat-tile-top">
            <span className="stat-tile-label">Channels Tracked</span>
            <span className="stat-tile-icon">⊡</span>
          </div>
          <div className="stat-tile-value">{channels.length}</div>
          <div className="stat-tile-sub">
            {activeCount} active, {channels.length - activeCount} paused
          </div>
        </div>

        <div className="stat-tile">
          <div className="stat-tile-top">
            <span className="stat-tile-label">Total Videos</span>
            <span className="stat-tile-icon">▷</span>
          </div>
          <div className="stat-tile-value">{totalVideos}</div>
          <div className="stat-tile-sub">Last 30 days</div>
        </div>

        <div className="stat-tile">
          <div className="stat-tile-top">
            <span className="stat-tile-label">Avg. Sentiment</span>
            <span className="stat-tile-icon">↑</span>
          </div>
          <div className="stat-tile-value">{avgSentiment}%</div>
          <div className="stat-tile-sub">Across all channels</div>
        </div>

        <div className="stat-tile">
          <div className="stat-tile-top">
            <span className="stat-tile-label">API Quota Used</span>
            <span className="stat-tile-icon">⚡</span>
          </div>
          <div className="stat-tile-value">74%</div>
          <div className="stat-tile-sub">7,420 / 10,000 daily</div>
        </div>
      </div>

      {/* Table */}
      <div className="table-card">
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Channel</th>
                <th>League</th>
                <th>Videos</th>
                <th>Sentiment</th>
                <th>Latest Video</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {channels.map((ch, i) => (
                <tr key={i}>
                  {/* Channel */}
                  <td>
                    <div className="channel-cell">
                      <div className="channel-avatar">{ch.initials}</div>
                      <div>
                        <div className="channel-name">{ch.name}</div>
                        <div className="channel-meta">
                          <span>{ch.handle}</span>
                          <span className="channel-meta-divider" />
                          <span>👤 {ch.subscribers}</span>
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* League */}
                  <td>
                    <span className="league-badge">{ch.league}</span>
                  </td>

                  {/* Videos */}
                  <td>
                    <span className="videos-count">{ch.videos}</span>
                  </td>

                  {/* Sentiment */}
                  <td>
                    <div className={`sentiment-cell ${sentimentClass(ch.sentimentTrend)}`}>
                      <span className="sentiment-arrow">
                        {sentimentArrow(ch.sentimentTrend)}
                      </span>
                      <span className="sentiment-value">{ch.sentiment}%</span>
                    </div>
                  </td>

                  {/* Latest Video */}
                  <td>
                    <div className="latest-video">
                      <div className="latest-video-title">
                        <span className="latest-video-play">▷</span>
                        {ch.latestVideo}
                      </div>
                      <div className="latest-video-views">{ch.views}</div>
                    </div>
                  </td>

                  {/* Toggle */}
                  <td>
                    <div className="toggle-wrapper">
                      <Toggle
                        checked={ch.active}
                        onChange={() => toggleChannel(i)}
                      />
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