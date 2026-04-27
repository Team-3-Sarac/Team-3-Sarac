import Badge from "../components/badge";
import { TrendingUp, TrendingDown, Minus, ShieldAlert, ShieldCheck, Shield } from "lucide-react";

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

function getRiskLabel(score: number): string {
  if (score >= 76) return "Critical";
  if (score >= 51) return "High";
  if (score >= 26) return "Medium";
  return "Low";
}

function hasRiskData(score: number | null | undefined, level: string | null | undefined): boolean {
  return score !== null && score !== undefined && level !== null && level !== undefined;
}

function getRiskBadgeTone(level: string): "pos" | "neu" | "neg" {
  switch (level.toLowerCase()) {
    case "low":
      return "pos";
    case "medium":
      return "neu";
    case "high":
    case "critical":
      return "neg";
    default:
      return "neu";
  }
}

function getRiskColor(level: string): string {
  switch (level.toLowerCase()) {
    case "low":
      return "text-emerald-400";
    case "medium":
      return "text-yellow-400";
    case "high":
      return "text-orange-400";
    case "critical":
      return "text-red-400";
    default:
      return "text-neutral-500";
  }
}

function getRiskIcon(level: string) {
  switch (level.toLowerCase()) {
    case "low":
      return ShieldCheck;
    case "medium":
      return Shield;
    case "high":
    case "critical":
      return ShieldAlert;
    default:
      return Shield;
  }
}

export default function ChannelRow({
  row,
  onRiskClick,
}: {
  row: ChannelRowData;
  onRiskClick?: () => void;
}) {

  const SentimentIcon =
    row.sentimentDir === "up"
      ? TrendingUp
      : row.sentimentDir === "down"
      ? TrendingDown
      : Minus;

  const sentimentColor =
    row.sentimentDir === "up"
      ? "text-emerald-400"
      : row.sentimentDir === "down"
      ? "text-red-400"
      : "text-neutral-500";

  const riskAvailable = hasRiskData(row.riskScore, row.riskLevel);
  const riskLevel = row.riskLevel || "low";
  const riskScore = row.riskScore ?? 0;
  const RiskIcon = getRiskIcon(riskLevel);
  const riskColor = getRiskColor(riskLevel);
  const riskBadgeTone = getRiskBadgeTone(riskLevel);

  return (
    <div className="grid grid-cols-12 items-center gap-4 px-6 py-4 transition-colors hover:bg-[#161616]">

      {/* Channel identity */}
      <div className="col-span-4 flex items-center gap-3 min-w-0">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/8 bg-white/5 text-[12px] font-bold text-neutral-300">
          {row.initials}
        </div>
        <div className="min-w-0">
          <div className="truncate text-[13px] font-semibold text-white/90">{row.name}</div>
          <div className="text-[11px] text-neutral-600">{row.handle}</div>
        </div>
      </div>

      {/* League */}
      <div className="col-span-2">
        <Badge tone="neutral">{row.league}</Badge>
      </div>

      {/* Videos */}
      <div className="col-span-1 text-right">
        <span className="tabular-nums text-[13px] text-neutral-400">{row.videos}</span>
      </div>

      {/* Sentiment */}
      <div className="col-span-1 flex items-center justify-end gap-2">
        <span className={`inline-flex items-center gap-1 text-[12px] tabular-nums ${sentimentColor}`}>
          <SentimentIcon className="h-3 w-3 shrink-0" />
          {row.sentimentPct != null ? `${Math.round(row.sentimentPct * 100)}%` : "N/A"}
        </span>
      </div>

      {/* Risk */}
      <div className="col-span-1 flex items-center justify-end gap-2">
        {riskAvailable ? (
          <button
            onClick={onRiskClick}
            className="inline-flex items-center gap-1.5 hover:opacity-80 transition-opacity"
            title={`Risk Score: ${riskScore} - ${getRiskLabel(riskScore)}`}
          >
            <span className={`inline-flex items-center gap-1 text-[12px] tabular-nums ${riskColor}`}>
              <RiskIcon className="h-3.5 w-3.5 shrink-0" />
              {Math.round(riskScore)}
            </span>
            <Badge tone={riskBadgeTone}>{getRiskLabel(riskScore)}</Badge>
          </button>
        ) : (
          <span className="text-[12px] text-neutral-500">—</span>
        )}
      </div>

      {/* Latest video */}
      <div className="col-span-3 min-w-0">
        <div className="truncate text-[12px] text-neutral-400">{row.latestTitle}</div>
        <div className="mt-0.5 text-[11px] text-neutral-600">{row.latestViews}</div>
      </div>
    </div>
  );
}