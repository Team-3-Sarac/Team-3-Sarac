"use client";
import { useEffect, useState } from "react";
import Skeleton from "../components/skeleton";
import SectionLabel from "../components/sectionLabel";
import Card from "../components/card";
import EmptyState from "../components/emptyState";
import KpiCard from "../components/kpiCard";
import CardHeader from "../components/cardHeader";
import ChannelRow from "../components/channelRow";
import RiskModal from "../components/riskModal";
import { getChannels, getDashboardKPIs, getVideos, getChannelRisk, getChannelsWithRisk } from "../../api/backend";
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
  sentimentPct: number | null;
  sentimentDir: "up" | "down" | "flat";
  latestTitle: string;
  latestViews: string;
  riskScore?: number | null;
  riskLevel?: "low" | "medium" | "high" | "critical" | null;
};

/* ---------------- Helpers ---------------- */

function useCountUp(target: number | null, duration = 1200) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (target === null) return;

    const finalTarget = target;
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
          <div className="col-span-3 flex flex-col gap-1.5">
            <Skeleton className="h-3.5 w-full" />
            <Skeleton className="h-3 w-16" />
          </div>
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
  const [channelsError, setChannelsError] = useState(false);
  const [kpisError, setKpisError] = useState(false);
  const [riskModalOpen, setRiskModalOpen] = useState(false);
  const [selectedChannelRisk, setSelectedChannelRisk] = useState<any>(null);
  const [riskLoading, setRiskLoading] = useState(false);

  const animatedChannels  = useCountUp(channels.length > 0 ? channels.length : null);
  const animatedVideos    = useCountUp(kpis?.videos_analyzed ?? null);
  const animatedSentiment = useCountUp(kpis ? kpis.avg_sentiment * 100 : null);

  const avgRiskScore = rows.length > 0 && rows.some(r => r.riskScore !== null)
    ? Math.round(rows.reduce((sum, r) => sum + (r.riskScore || 0), 0) / rows.filter(r => r.riskScore !== null).length)
    : null;

  const channelsWithRisk = rows.filter(r => r.riskScore !== null).length;

  useEffect(() => {
    async function fetchData() {
      const [channelsRes, kpisRes, videosRes, riskRes] = await Promise.allSettled([
        getChannels(),
        getDashboardKPIs(),
        getVideos({ limit: 100 }),
        getChannelsWithRisk({ limit: 500 }),
      ]);

      // KPIs — non-fatal, shown in KPI cards only
      if (kpisRes.status === "fulfilled") {
        setKpis(kpisRes.value);
      } else {
        console.error("[Channels] Failed to fetch KPIs:", kpisRes.reason);
        setKpisError(true);
      }

      // Channels + videos + risk — all needed to build rows
      if (
        channelsRes.status === "fulfilled" &&
        videosRes.status === "fulfilled"
      ) {
        const channelList: Channel[] = channelsRes.value.channels || [];
        setChannels(channelList);

        const riskMap = new Map<string, { riskScore: number | null; riskLevel: string | null }>();
        if (riskRes.status === "fulfilled") {
          (riskRes.value.channels || []).forEach((c: any) => {
            riskMap.set(c.channel_id, {
              riskScore: c.risk_score,
              riskLevel: c.risk_level,
            });
          });
        } else {
          console.warn("[Channels] Failed to fetch risk data (non-fatal):", riskRes.reason);
        }

        const transformed: ChannelRowData[] = channelList.map((c: Channel) => {
          const channelVideos =
            videosRes.value.videos?.filter((v: any) => v.channel_id === c.channel_id) || [];
          const latestVideo = channelVideos[0];
          const videosWithSentiment = channelVideos.filter((v: any) => v.sentiment_pct !== null && v.sentiment_pct !== undefined);
          const avgSentiment = videosWithSentiment.length > 0
            ? videosWithSentiment.reduce((sum: number, v: any) => sum + v.sentiment_pct, 0) / videosWithSentiment.length
            : null;
          const riskData = riskMap.get(c.channel_id);

          return {
            id: c.channel_id,
            initials: getInitials(c.channel_name),
            name: c.channel_name,
            handle: `@${c.channel_name.replace(/\s+/g, "")}`,
            subs: formatSubs(c.total_views),
            league: getMostCommonLeague(channelVideos),
            videos: c.video_count,
            sentimentPct: avgSentiment,
            sentimentDir: avgSentiment == null ? "flat" : avgSentiment > 0.6 ? "up" : avgSentiment < 0.4 ? "down" : "flat",
            latestTitle: latestVideo?.title || "No recent videos",
            latestViews: latestVideo ? formatViews(latestVideo.view_count) : "0 views",
            riskScore: riskData?.riskScore ?? null,
            riskLevel: (riskData?.riskLevel ?? null) as ChannelRowData["riskLevel"],
          };
        });

        setRows(transformed);
      } else {
        if (channelsRes.status === "rejected") {
          console.error("[Channels] Failed to fetch channels:", channelsRes.reason);
        }
        if (videosRes.status === "rejected") {
          console.error("[Channels] Failed to fetch videos:", videosRes.reason);
        }
        setChannelsError(true);
      }

      setLoading(false);
    }

    fetchData();
  }, []);

  const handleRiskClick = async (channelId: string) => {
    setRiskLoading(true);
    try {
      const riskData = await getChannelRisk(channelId);
      setSelectedChannelRisk(riskData);
      setRiskModalOpen(true);
    } catch (err) {
      console.error("Failed to fetch channel risk:", err);
      // TODO: optionally show a toast/error message here
    } finally {
      setRiskLoading(false);
    }
  };

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

      <div className="relative z-10 mx-auto max-w-7xl px-6 py-12">

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
            icon={<Video className="h-3.5 w-3.5" />}
            title="Total Videos"
            value={kpisError ? "—" : kpis ? formatNumber(animatedVideos) : "—"}
            sub={kpisError ? "Failed to load" : loading ? "Loading…" : "Across all tracked channels"}
            loading={loading}
          />
          <KpiCard
            icon={<ShieldAlert className="h-3.5 w-3.5" />}
            title="Avg. Risk Score"
            value={loading || channelsError || avgRiskScore === null ? "—" : `${avgRiskScore}`}
            sub={channelsError ? "Failed to load" : loading ? "Loading…" : `${channelsWithRisk}/${rows.length} channels analyzed`}
            loading={loading}
          />
          <KpiCard
            icon={<Activity className="h-3.5 w-3.5" />}
            title="Avg. Sentiment"
            value={kpisError || !kpis ? "—" : `${Math.round(animatedSentiment)}%`}
            sub={
              kpisError ? "Failed to load" :
              loading ? "Loading…" :
              kpis
                ? kpis.avg_sentiment >= 0.6 ? "Positive overall"
                : kpis.avg_sentiment >= 0.4 ? "Neutral overall"
                : "Negative overall"
                : "—"
            }
            loading={loading}
          />
          <KpiCard
            icon={<Users className="h-3.5 w-3.5" />}
            title="Channels Tracked"
            value={channelsError ? "—" : formatNumber(animatedChannels)}
            sub={channelsError ? "Failed to load" : loading ? "Loading…" : "Monitored creator accounts"}
            loading={loading}
          />
        </div>

        {/* ── Channel table ── */}
        <div className="mt-6">
          <Card>
            <CardHeader
              title="Creator Overview"
              subtitle="Performance and risk calculation across all monitored channels"
            />
            {/* Table header */}
            <div className="grid grid-cols-12 items-center gap-4 border-b border-white/6 px-6 py-3">
              <div className="col-span-4 text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Channel</div>
              <div className="col-span-2 text-[11px] font-semibold uppercase tracking-widest text-neutral-600">League</div>
              <div className="col-span-1 text-right text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Videos</div>
              <div className="col-span-1 text-right text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Sentiment</div>
              <div className="col-span-1 text-right text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Risk</div>
              <div className="col-span-3 text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Latest Video</div>
            </div>

            <div className="divide-y divide-white/4">
              {loading ? (
                <TableSkeleton />
              ) : channelsError ? (
                <EmptyState message="Failed to load channels" />
              ) : rows.length === 0 ? (
                <EmptyState message="No channels available" />
              ) : (
                rows.map((r) => (
                  <ChannelRow
                    key={r.id}
                    row={r}
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
