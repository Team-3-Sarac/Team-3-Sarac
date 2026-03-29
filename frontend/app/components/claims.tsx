"use client";
import { useEffect, useState } from "react";
import { getClaims, getNarratives } from "../../api/backend";

type Claim = {
  id: string;
  narrative_id: string;
  text: string;
  video_id: string;
  created_at: string;
  mention_count?: number;
  confidence?: number;
  sentiment?: string;
};

type Narrative = {
  id: string;
  title: string;
  league: string | null;
  claims_ids: string[];
  created_at: string;
};

export default function ClaimsPanel() {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [narratives, setNarratives] = useState<Narrative[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        const [claimsRes, narrativesRes] = await Promise.all([
          getClaims({ limit: 10 }),
          getNarratives(),
        ]);
        setClaims(claimsRes.claims || []);
        setNarratives(narrativesRes.narratives || []);
      } catch (err) {
        console.error("Failed to fetch claims:", err);
        setError(true);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const getClaimLeague = (narrativeId: string): string | null => {
    const narrative = narratives.find((n) => n.id === narrativeId);
    return narrative?.league || null;
  };

  const getSentimentTone = (sentiment: string | undefined) => {
    if (sentiment === "positive") return "green";
    if (sentiment === "negative") return "red";
    return "yellow";
  };

  return (
    <div className="rounded-xl border border-white/[0.07] bg-[#0f0f0f]">
      <div className="border-b border-white/6 px-5 py-5">
        <div
          className="text-sm font-semibold"
          style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
        >
          Emerging Claims
        </div>
        <div className="text-xs text-neutral-400">
          Repeated claims and narratives extracted from soccer video coverage
        </div>
      </div>

      <div className="divide-y divide-white/4">
        {loading ? (
          <div className="divide-y divide-white/4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="px-5 py-4">
                <div className="animate-pulse space-y-2">
                  <div className="h-3.5 w-3/4 rounded bg-white/4" />
                  <div className="h-3.5 w-1/2 rounded bg-white/4" />
                  <div className="mt-3 flex gap-2">
                    <div className="h-5 w-20 rounded-md bg-white/4" />
                    <div className="h-5 w-24 rounded-md bg-white/4" />
                    <div className="h-5 w-16 rounded-md bg-white/4" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="flex h-32 items-center justify-center text-sm text-neutral-600">
            Failed to load claims
          </div>
        ) : claims.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-sm text-neutral-500">
            No claims available
          </div>
        ) : (
          claims.slice(0, 5).map((item) => {
            const league = getClaimLeague(item.narrative_id);
            return (
              <div key={item.id} className="px-5 py-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-white">{item.text}</p>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      {item.mention_count !== undefined && (
                        <ClaimBadge label={`${item.mention_count} mentions`} tone="neutral" />
                      )}
                      {item.confidence !== undefined && (
                        <ClaimBadge label={`${item.confidence}% confidence`} tone="blue" />
                      )}
                      {item.sentiment && (
                        <ClaimBadge
                          label={item.sentiment}
                          tone={getSentimentTone(item.sentiment)}
                        />
                      )}
                      {league && <ClaimBadge label={league} tone="neutral" />}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function ClaimBadge({ label, tone = "neutral" }: { label: string; tone?: "neutral" | "green" | "red" | "yellow" | "blue" }) {
  const styles = {
    neutral: "border-neutral-800 bg-neutral-900/50 text-neutral-300",
    green: "border-emerald-500/20 bg-emerald-500/10 text-emerald-300",
    red: "border-red-500/20 bg-red-500/10 text-red-300",
    yellow: "border-amber-500/20 bg-amber-500/10 text-amber-300",
    blue: "border-sky-500/20 bg-sky-500/10 text-sky-300",
  };

  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-1 text-[11px] ${styles[tone]}`}>
      {label}
    </span>
  );
}
