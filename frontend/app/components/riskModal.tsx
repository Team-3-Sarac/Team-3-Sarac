"use client";

import { X } from "lucide-react";
import Badge from "./badge";
import { ShieldAlert, ShieldCheck, Shield } from "lucide-react";

type RiskBreakdown = {
  self_harm?: number;
  violence?: number;
  illegal_activities?: number;
  misinformation?: number;
  hate_speech?: number;
  harassment?: number;
  toxicity?: number;
};

type HighRiskVideo = {
  video_id: string;
  title: string;
  risk_score?: number | null;
  risk_level?: string | null;
};

type RiskModalProps = {
  isOpen: boolean;
  onClose: () => void;
  channelData: {
    channel_id: string;
    channel_name: string;
    video_count: number;
    videos_with_risk: number;
    avg_risk_score?: number | null;
    risk_level?: string | null;
    risk_breakdown?: RiskBreakdown | null;
    high_risk_videos?: HighRiskVideo[];
  } | null;
};

function getRiskLabel(score: number): string {
  if (score >= 76) return "Critical";
  if (score >= 51) return "High";
  if (score >= 26) return "Medium";
  return "Low";
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

function getRiskBgColor(level: string): string {
  switch (level.toLowerCase()) {
    case "low":
      return "bg-emerald-500/20 border-emerald-500/40";
    case "medium":
      return "bg-yellow-500/20 border-yellow-500/40";
    case "high":
      return "bg-orange-500/20 border-orange-500/40";
    case "critical":
      return "bg-red-500/20 border-red-500/40";
    default:
      return "bg-neutral-500/20 border-neutral-500/40";
  }
}

function getRiskCategoryLabel(key: string): string {
  const labels: Record<string, string> = {
    self_harm: "Self-Harm References",
    violence: "Violence or Threats",
    illegal_activities: "Illegal Activities",
    misinformation: "Misinformation",
    hate_speech: "Hate Speech",
    harassment: "Harassment",
    toxicity: "Toxicity",
  };
  return labels[key] || key;
}

function ProgressBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="h-2 w-full rounded-full bg-neutral-800 overflow-hidden">
      <div
        className={`h-full rounded-full ${color}`}
        style={{ width: `${Math.min(100, Math.max(0, value * 100))}%` }}
      />
    </div>
  );
}

export default function RiskModal({ isOpen, onClose, channelData }: RiskModalProps) {
  if (!isOpen || !channelData) return null;

  const riskAvailable = channelData.avg_risk_score !== null && channelData.avg_risk_score !== undefined;
  const riskScore = channelData.avg_risk_score ?? 0;
  const riskLevel = channelData.risk_level || "low";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-[#0f0f0f] border border-white/10 rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 flex items-center justify-between px-6 py-4 border-b border-white/10 bg-[#0f0f0f]/95 backdrop-blur">
          <div>
            <h2 className="text-lg font-semibold text-white">Creator Risk Analysis</h2>
            <p className="text-sm text-neutral-400">{channelData.channel_name}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/5 transition-colors"
          >
            <X className="h-5 w-5 text-neutral-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Overall Risk Score */}
          <div className={`p-6 rounded-xl border ${riskAvailable ? getRiskBgColor(riskLevel) : "bg-neutral-500/10 border-white/10"}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-neutral-400">Overall Risk Level</p>
                <p className={`text-3xl font-bold mt-1 ${riskAvailable ? getRiskColor(riskLevel) : "text-neutral-400"}`}>
                  {riskAvailable ? getRiskLabel(riskScore) : "Unavailable"}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium text-neutral-400">Risk Score</p>
                <p className={`text-4xl font-bold mt-1 ${riskAvailable ? getRiskColor(riskLevel) : "text-neutral-400"}`}>
                  {riskAvailable ? Math.round(riskScore) : "—"}
                </p>
                <p className="text-xs text-neutral-500">{riskAvailable ? "out of 100" : "Awaiting analysis"}</p>
              </div>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-white/5 border border-white/10">
              <p className="text-xs text-neutral-500">Videos Analyzed</p>
              <p className="text-2xl font-bold text-white mt-1">{channelData.videos_with_risk}</p>
            </div>
            <div className="p-4 rounded-lg bg-white/5 border border-white/10">
              <p className="text-xs text-neutral-500">Total Videos</p>
              <p className="text-2xl font-bold text-white mt-1">{channelData.video_count}</p>
            </div>
            <div className="p-4 rounded-lg bg-white/5 border border-white/10">
              <p className="text-xs text-neutral-500">Coverage</p>
              <p className="text-2xl font-bold text-white mt-1">
                {channelData.video_count > 0
                  ? Math.round((channelData.videos_with_risk / channelData.video_count) * 100)
                  : 0}%
              </p>
            </div>
          </div>

          {/* Risk Breakdown */}
          {riskAvailable && channelData.risk_breakdown && Object.keys(channelData.risk_breakdown).length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-white mb-4">Risk Category Breakdown</h3>
              <div className="space-y-3">
                {Object.entries(channelData.risk_breakdown).map(([key, value]) => (
                  <div key={key} className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-neutral-300">
                        {getRiskCategoryLabel(key)}
                      </span>
                      <span className="text-sm font-medium text-neutral-400">
                        {Math.round((value || 0) * 100)}%
                      </span>
                    </div>
                    <ProgressBar
                      value={value || 0}
                      color={
                        (value || 0) >= 0.75
                          ? "bg-red-500"
                          : (value || 0) >= 0.5
                          ? "bg-orange-500"
                          : (value || 0) >= 0.25
                          ? "bg-yellow-500"
                          : "bg-emerald-500"
                      }
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* High Risk Videos */}
          {channelData.high_risk_videos && channelData.high_risk_videos.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-red-400" />
                High-Risk Videos
              </h3>
              <div className="space-y-2">
                {channelData.high_risk_videos.map((video) => (
                  <div
                    key={video.video_id}
                    className="p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-white truncate">{video.title}</p>
                        <p className="text-xs text-neutral-500 mt-1">{video.video_id}</p>
                      </div>
                      <Badge
                        tone={
                          video.risk_level === "critical" || video.risk_level === "high"
                            ? "neg"
                            : "neu"
                        }
                      >
                        {video.risk_level
                          ? getRiskLabel(video.risk_score || 0)
                          : "Unknown"}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Info Note */}
          <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
            <p className="text-xs text-blue-300">
              <strong>Note:</strong> Risk scores are calculated using AI analysis of video transcripts.
              {riskAvailable
                ? " Scores are aggregated at the channel level from all analyzed videos. Categories with higher scores indicate more frequent or severe risk indicators."
                : " This creator does not have transcript-backed risk analysis yet, so no score is shown."}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
