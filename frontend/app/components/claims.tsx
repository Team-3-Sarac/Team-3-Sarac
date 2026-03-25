"use client";
import { useEffect, useState } from "react";
import { getClaims, getNarratives } from "../../api/backend";

type Claim = {
  id: string;
  narrative_id: string;
  text: string;
  video_id: string;
  created_at: string;
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
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const getNarrativeTitle = (narrativeId: string): string => {
    const narrative = narratives.find((n) => n.id === narrativeId);
    return narrative?.title || "General Claim";
  };

  const getClaimLeague = (narrativeId: string): string | null => {
    const narrative = narratives.find((n) => n.id === narrativeId);
    return narrative?.league || null;
  };

  const getMockMetrics = (index: number) => ({
    confidence: 75 + (index % 20),
    sentiment: ["positive", "neutral", "negative"][index % 3] as "positive" | "neutral" | "negative",
    mentions: 50 + (index * 12),
  });

  if (loading) {
    return (
      <div className="rounded-2xl border border-neutral-800 bg-neutral-950/40 shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
        <div className="flex h-32 items-center justify-center text-neutral-500">
          Loading claims...
        </div>
      </div>
    );
  }

  const displayClaims = claims.length > 0 ? claims : getFallbackClaims();

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-950/40 shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
      <div className="border-b border-neutral-800 px-5 py-4">
        <div className="text-sm font-semibold">Emerging Claims</div>
        <div className="text-xs text-neutral-400">
          Repeated claims and narratives extracted from soccer video coverage
        </div>
      </div>

      <div className="divide-y divide-neutral-800">
        {displayClaims.slice(0, 5).map((item, index) => {
          const metrics = getMockMetrics(index);
          const leagues = getClaimLeague(item.narrative_id);
          
          return (
            <div key={item.id || index} className="px-5 py-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-white">
                    {item.text || getFallbackClaims()[index]?.text || "Claim data unavailable"}
                  </p>

                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <ClaimBadge label={`${metrics.mentions} mentions`} tone="neutral" />
                    <ClaimBadge label={`${metrics.confidence}% confidence`} tone="blue" />
                    <ClaimBadge
                      label={metrics.sentiment}
                      tone={metrics.sentiment === "positive" ? "green" : metrics.sentiment === "negative" ? "red" : "yellow"}
                    />
                    {leagues && <ClaimBadge key={leagues} label={leagues} tone="neutral" />}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
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

function getFallbackClaims(): Claim[] {
  return [
    { id: "1", narrative_id: "1", text: "Arsenal are the strongest title contenders this season.", video_id: "", created_at: "" },
    { id: "2", narrative_id: "2", text: "VAR decisions are having too much influence on match results.", video_id: "", created_at: "" },
    { id: "3", narrative_id: "3", text: "Real Madrid have more depth than Barcelona this season.", video_id: "", created_at: "" },
    { id: "4", narrative_id: "4", text: "Kane has completely transformed Bayern's attack.", video_id: "", created_at: "" },
    { id: "5", narrative_id: "5", text: "Injuries are hurting Napoli's title chances.", video_id: "", created_at: "" },
  ];
}
