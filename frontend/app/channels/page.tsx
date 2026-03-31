"use client";
import { useEffect, useState } from "react";
import Skeleton from "../components/skeleton";
import SectionLabel from "../components/sectionLabel";
import Card from "../components/card";
import EmptyState from "../components/emptyState";
import KpiCard from "../components/kpiCard";
import ChannelRow from "../components/channelRow";
import RiskModal from "../components/riskModal";
import { getChannels, getDashboardKPIs, getVideos, getChannelRisk } from "../../api/backend";
import {
  Video,
  Activity,
  Users,
  Zap,
  ShieldAlert,
} from "lucide-react";

/* ---------------- Types ---------------- */

type Channel = {
  channel_id: string;
  channel_name: string;
  video_count: number;
  total_views: number;
  total_likes: number;
  total_comments: number;
};

type ChannelRowData = {
  id: string;
  initials: string;
  name: string;
  handle: string;
  subs: string;
  league: string;
  videos: number;
  sentimentPct: number;
  sentimentDir: "up" | "down" | "flat";
  latestTitle: string;
  latestViews: string;
  active: boolean;
  riskScore?: number | null;
  riskLevel?: "low" | "medium" | "high" | "critical" | null;
};

/* ---------------- Helpers ---------------- */

function useCountUp(target: number | null, duration = 1200) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (target === null) return;

    const finalTarget = target; // TS now knows this is a number
    const startTime = performance.now();

    function animate(now: number) {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.floor(eased * finalTarget));

      if (progress < 1) requestAnimationFrame(animate);
    }

    requestAnimationFrame(animate);
  }, [target, duration]);

  return value;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join("");
}

function formatNumber(num: number): string {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toLocaleString();
}

function formatSubs(views: number): string {
  if (views >= 1_000_000) return `${(views / 1_000_000).toFixed(1)}M`;
  if (views >= 1_000) return `${(views / 1_000).toFixed(1)}K`;
  return views.toString();
}

function formatViews(views: number): string {
  if (views >= 1_000_000) return `${(views / 1_000_000).toFixed(1)}M views`;
  if (views >= 1_000) return `${(views / 1_000).toFixed(0)}K views`;
  return `${views} views`;
}

function getMostCommonLeague(videos: any[]): string {
  if (!videos.length) return "Multi-League";
  const counts: Record<string, number> = {};
  for (const v of videos) {
    if (v.league) counts[v.league] = (counts[v.league] || 0) + 1;
  }
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  return sorted[0]?.[0] || "Multi-League";
}

function getSentimentLabel(pct: number): string {
  if (pct >= 60) return "Positive";
  if (pct >= 40) return "Neutral";
  return "Negative";
}

/* ---------------- Table Skeleton ---------------- */

function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="divide-y divide-white/4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="grid grid-cols-12 items-center gap-4 px-6 py-4">
          <div className="col-span-4 flex items-center gap-3">
            <Skeleton className="h-9 w-9 rounded-lg" />
            <div className="flex flex-col gap-1.5">
              <Skeleton className="h-3.5 w-28" />
              <Skeleton className="h-3 w-20" />
            </div>
          </div>
          <div className="col-span-2"><Skeleton className="h-5 w-20 rounded-md" /></div>
          <div className="col-span-1 flex justify-end"><Skeleton className="h-3.5 w-8" /></div>
          <div className="col-span-2 flex justify-end gap-2">
            <Skeleton className="h-3.5 w-10" />
            <Skeleton className="h-5 w-16 rounded-md" />
          </div>
          <div className="col-span-2 flex flex-col gap-1.5">
            <Skeleton className="h-3.5 w-full" />
            <Skeleton className="h-3 w-16" />
          </div>
          <div className="col-span-1 flex justify-end"><Skeleton className="h-5 w-9 rounded-full" /></div>
        </div>
      ))}
    </div>
  );
}

/* ================================================================
   PAGE
================================================================ */

export default function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [kpis, setKpis] = useState<{ videos_analyzed: number; avg_sentiment: number } | null>(null);
  const [rows, setRows] = useState<ChannelRowData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [riskModalOpen, setRiskModalOpen] = useState(false);
  const [selectedChannelRisk, setSelectedChannelRisk] = useState<any>(null);
  const [riskLoading, setRiskLoading] = useState(false);

  const animatedChannels = useCountUp(channels.length ?? null);
  const animatedVideos = useCountUp(kpis?.videos_analyzed ?? null);
  const animatedSentiment = useCountUp(kpis?.avg_sentiment ?? null);

  // Calculate average risk score
  const avgRiskScore = rows.length > 0
    ? Math.round(rows.reduce((sum, r) => sum + (r.riskScore || 0), 0) / rows.length)
    : 0;

  const highRiskCount = rows.filter((r) => r.riskLevel === "high" || r.riskLevel === "critical").length;


  useEffect(() => {
    async function fetchData() {
      try {
        const [channelsRes, kpisRes, videosRes] = await Promise.all([
          getChannels(),
          getDashboardKPIs(),
          getVideos({ limit: 100 }),
        ]);
        setChannels(channelsRes.channels || []);
        setKpis(kpisRes);

        const transformed: ChannelRowData[] = (channelsRes.channels || []).map((c: Channel) => {
          const channelVideos =
            videosRes.videos?.filter((v: any) => v.channel_id === c.channel_id) || [];
          const latestVideo = channelVideos[0];
          const avgSentiment = Math.min(
            95,
            Math.max(30, 60 + Math.round((c.total_likes / Math.max(c.total_views, 1)) * 100))
          );
          // Mock risk data for now (will be replaced with real API data)
          const mockRiskScore = Math.floor(Math.random() * 100);
          const mockRiskLevel = mockRiskScore >= 76 ? "critical" : mockRiskScore >= 51 ? "high" : mockRiskScore >= 26 ? "medium" : "low";
          
          return {
            id: c.channel_id,
            initials: getInitials(c.channel_name),
            name: c.channel_name,
            handle: `@${c.channel_name.replace(/\s+/g, "")}`,
            subs: formatSubs(c.total_views),
            league: getMostCommonLeague(channelVideos),
            videos: c.video_count,
            sentimentPct: avgSentiment,
            sentimentDir: avgSentiment > 70 ? "up" : avgSentiment < 50 ? "down" : "flat",
            latestTitle: latestVideo?.title || "No recent videos",
            latestViews: latestVideo ? formatViews(latestVideo.view_count) : "0 views",
            active: true,
            riskScore: mockRiskScore,
            riskLevel: mockRiskLevel,
          };
        });
        setRows(transformed);
      } catch (err) {
        console.error("Failed to fetch channels data:", err);
        setError(true);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const toggleActive = (id: string) => {
    setRows((prev) =>
      prev.map((r) => (r.id === id ? { ...r, active: !r.active } : r))
    );
  };

  const handleRiskClick = async (channelId: string) => {
    setRiskLoading(true);
    try {
      const riskData = await getChannelRisk(channelId);
      setSelectedChannelRisk(riskData);
      setRiskModalOpen(true);
    } catch (err) {
      console.error("Failed to fetch channel risk:", err);
      // Show modal with mock data if API fails
      setSelectedChannelRisk({
        channel_id: channelId,
        channel_name: rows.find((r) => r.id === channelId)?.name || "Unknown",
        video_count: rows.find((r) => r.id === channelId)?.videos || 0,
        videos_with_risk: Math.floor(Math.random() * 20) + 5,
        avg_risk_score: rows.find((r) => r.id === channelId)?.riskScore || 0,
        risk_level: rows.find((r) => r.id === channelId)?.riskLevel || "low",
        risk_breakdown: {
          self_harm: Math.random() * 0.3,
          violence: Math.random() * 0.5,
          illegal_activities: Math.random() * 0.2,
          misinformation: Math.random() * 0.6,
          hate_speech: Math.random() * 0.3,
          harassment: Math.random() * 0.4,
          toxicity: Math.random() * 0.5,
        },
        high_risk_videos: [],
      });
      setRiskModalOpen(true);
    } finally {
      setRiskLoading(false);
    }
  };

  const activeCount = rows.filter((r) => r.active).length;
  const pausedCount = rows.filter((r) => !r.active).length;

  return (
    <div className="relative min-h-screen w-full overflow-x-hidden bg-[#080808] text-white">

      {/* ── Grid background ── */}
      <div className="pointer-events-none fixed inset-0 z-0 opacity-[0.03]">
        <div
          className="h-full w-full"
          style={{
            backgroundImage: `
              linear-gradient(to right, white 1px, transparent 1px),
              linear-gradient(to bottom, white 1px, transparent 1px)
            `,
            backgroundSize: "80px 80px",
          }}
        />
      </div>

      <div className="relative z-10 mx-auto max-w-6xl px-6 py-12">

        {/* ── Page header ── */}
        <div className="mb-10">
          <SectionLabel>Monitoring</SectionLabel>
          <h1
            className="mt-2 text-[clamp(2rem,4vw,2.8rem)] font-black leading-tight tracking-[-0.02em]"
            style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
          >
            Channels
          </h1>
          <p className="mt-2 text-sm text-neutral-500">
            Explore performance trends from soccer-focused YouTube creators
          </p>
        </div>

        {/* ── Accent line ── */}
        <div className="mb-6 h-px w-full bg-linear-to-r from-transparent via-teal-500/30 to-transparent" />

        {/* ── KPIs ── */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <KpiCard
            icon={<Users className="h-3.5 w-3.5" />}
            title="Channels Tracked"
            value={error ? "—" : formatNumber(animatedChannels)}
            sub={error ? "Failed to load" : loading ? "Loading…" : `${activeCount} active, ${pausedCount} paused`}
            loading={loading}
          />
          <KpiCard
            icon={<Video className="h-3.5 w-3.5" />}
            title="Total Videos"
            value={error ? "—" : kpis ? formatNumber(animatedVideos) : "—"}
            sub={error ? "Failed to load" : "Across all tracked channels"}
            loading={loading}
          />
          <KpiCard
            icon={<Activity className="h-3.5 w-3.5" />}
            title="Avg. Sentiment"
            value={loading || !kpis ? "—" : `${Math.round(animatedSentiment)}%`}
            sub={
              error ? "Failed to load" :
              kpis
                ? kpis.avg_sentiment >= 60 ? "Positive overall"
                : kpis.avg_sentiment >= 40 ? "Neutral overall"
                : "Negative overall"
                : "Loading…"
            }
            loading={loading}
          />
          <KpiCard
            icon={<Zap className="h-3.5 w-3.5" />}
            title="API Quota Used"
            value="N/A"
            sub="Not available"
            loading={false}
          />
          <KpiCard
            icon={<ShieldAlert className="h-3.5 w-3.5" />}
            title="Avg Risk Score"
            value={loading || error ? "—" : `${avgRiskScore}`}
            sub={error ? "Failed to load" : `${highRiskCount} high-risk channels`}
            loading={loading}
          />
        </div>

        {/* ── Channel table ── */}
        <div className="mt-6">
          <Card>
            {/* Table header */}
            <div className="grid grid-cols-12 items-center gap-4 border-b border-white/6 px-6 py-3">
              <div className="col-span-4 text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Channel</div>
              <div className="col-span-2 text-[11px] font-semibold uppercase tracking-widest text-neutral-600">League</div>
              <div className="col-span-1 text-right text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Videos</div>
              <div className="col-span-1 text-right text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Sentiment</div>
              <div className="col-span-1 text-right text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Risk</div>
              <div className="col-span-2 text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Latest Video</div>
              <div className="col-span-1 text-right text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Active</div>
            </div>

            <div className="divide-y divide-white/4">
              {loading ? (
                <TableSkeleton />
              ) : error ? (
                <EmptyState message="Failed to load channels" />
              ) : rows.length === 0 ? (
                <EmptyState message="No channels available" />
              ) : (
                rows.map((r) => (
                  <ChannelRow
                    key={r.id}
                    row={r}
                    onToggle={() => toggleActive(r.id)}
                    onRiskClick={() => handleRiskClick(r.id)}
                  />
                ))
              )}
            </div>
          </Card>
        </div>

      </div>

      {/* Risk Detail Modal */}
      <RiskModal
        isOpen={riskModalOpen}
        onClose={() => setRiskModalOpen(false)}
        channelData={selectedChannelRisk}
      />
    </div>
  );
}
