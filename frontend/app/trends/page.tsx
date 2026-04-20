"use client";
import { useEffect, useState } from "react";
import Skeleton from "../components/skeleton";
import Card from "../components/card";
import CardHeader from "../components/cardHeader";
import BarChart from "../components/barChart";
import LineChart from "../components/lineChart";
import Badge from "../components/badge";
import TopicRow from "../components/topicRow";
import SectionLabel from "../components/sectionLabel";
import EmptyState from "../components/emptyState";
import { getTrends, getNarratives, getDashboardClaims } from "../../api/backend";
import { ArrowUpDown } from "lucide-react";

/* ---------------- Types ---------------- */

type Trend = {
  id: string;
  narrative_id: string;
  league: string | null;
  time_window: string;
  mention_count: number;
  trending_direction: string;
  score: number;
  created_at: string;
  category?: string | null;
};

type Narrative = {
  id: string;
  title: string;
  league: string | null;
  claims_ids: string[];
  created_at: string;
  category?: string | null;
};

type League = {
  league: string;
  count: number;
  status: string;
};

type Claim = {
  id: string;
  claim_text: string;
  sentiment?: string | null;
  sentiment_pct?: number | null;
  confidence_score?: number | null;
  mentions?: number;
  narrative_category?: string | null;
  created_at: string;
};

/* ---------------- Constants ---------------- */

const CATEGORIES = ["All", "Transfers", "Injuries", "Tactics", "Controversy"] as const;
const CATEGORY_COLORS: Record<string, string> = {
  Transfers:   "hover:text-emerald-400 data-[active=true]:text-emerald-400",
  Injuries:    "hover:text-red-400     data-[active=true]:text-red-400",
  Tactics:     "hover:text-sky-400     data-[active=true]:text-sky-400",
  Controversy: "hover:text-amber-400   data-[active=true]:text-amber-400",
};
type Category = (typeof CATEGORIES)[number];

type SortDir = "desc" | "asc";

/* ---------------- Helpers ---------------- */

function getChangeDir(direction: string): "up" | "down" | "flat" {
  if (direction === "up") return "up";
  if (direction === "down") return "down";
  return "flat";
}

function formatChange(direction: string, mentionCount: number): string {
  if (direction === "up") return `+${Math.min(Math.round(mentionCount / 10), 50)}%`;
  if (direction === "down") return `-${Math.min(Math.round(mentionCount / 10), 20)}%`;
  return "0%";
}

function getTopicLeague(trend: Trend): string[] {
  if (!trend.league) return ["Multi-League"];
  return [trend.league.length > 12 ? trend.league.substring(0, 12) + "…" : trend.league];
}

function getNarrativeCategory(trend: Trend, narratives: Narrative[]): string | null {
  const scores: Record<string, number> = {
    transfers: (trend as any).transfers ?? 0,
    injuries: (trend as any).injuries ?? 0,
    tactics: (trend as any).tactics ?? 0,
    controversy: (trend as any).controversy ?? 0,
  };
  const top = Object.entries(scores).sort((a, b) => b[1] - a[1])[0];
  if (top && top[1] > 0) return top[0];
  const narrative = narratives.find((n) => n.id === trend.narrative_id);
  return narrative?.category || trend.category || null;
}

function matchesCategory(cat: string | null, filter: Category): boolean {
  if (filter === "All") return true;
  if (!cat) return false;
  return cat.toLowerCase() === filter.toLowerCase();
}

function sortTrends(trends: Trend[], dir: SortDir): Trend[] {
  return [...trends].sort((a, b) =>
    dir === "desc"
      ? b.mention_count - a.mention_count
      : a.mention_count - b.mention_count
  );
}

function getSentimentBadgeTone(sentiment?: string | null): "pos" | "neu" | "neg" {
  if (sentiment === "positive") return "pos";
  if (sentiment === "negative") return "neg";
  return "neu";
}

function getSentimentLabel(sentiment?: string | null): string {
  if (sentiment === "positive") return "Positive";
  if (sentiment === "negative") return "Negative";
  return "Neutral";
}

/* ---------------- Sub-components ---------------- */

function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="divide-y divide-white/4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="grid grid-cols-12 gap-4 px-6 py-4">
          <div className="col-span-5 flex items-center gap-3">
            <Skeleton className="h-3.5 w-3.5 rounded" />
            <Skeleton className="h-3.5 w-40" />
          </div>
          <div className="col-span-3 flex items-center">
            <Skeleton className="h-2.5 w-28 rounded-full" />
          </div>
          <div className="col-span-1 flex justify-end"><Skeleton className="h-3.5 w-10" /></div>
          <div className="col-span-1 flex justify-end"><Skeleton className="h-3.5 w-12" /></div>
          <div className="col-span-2 flex justify-end"><Skeleton className="h-5 w-16 rounded-md" /></div>
        </div>
      ))}
    </div>
  );
}

function ClaimSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="divide-y divide-white/4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="px-6 py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 flex flex-col gap-2">
              <Skeleton className="h-3.5 w-full" />
              <Skeleton className="h-3.5 w-4/5" />
              <div className="flex gap-2 mt-1">
                <Skeleton className="h-5 w-20 rounded-md" />
                <Skeleton className="h-5 w-16 rounded-md" />
              </div>
            </div>
            <div className="flex flex-col gap-2.5 items-end shrink-0 pt-0.5">
              <Skeleton className="h-3 w-28" />
              <Skeleton className="h-3 w-28" />
              <Skeleton className="h-3 w-20" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function MiniBar({ value, tone }: { value: number; tone: "pos" | "neg" | "neu" | "conf" | "teal" }) {
  const colors = {
    pos:  "bg-emerald-400",
    neg:  "bg-red-400",
    neu:  "bg-neutral-500",
    conf: "bg-sky-400",
    teal: "bg-teal-400",
  };
  return (
    <div className="flex items-center gap-2">
      <div className="h-1 w-20 rounded-full bg-white/8 overflow-hidden">
        <div
          className={`h-full rounded-full ${colors[tone]}`}
          style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
        />
      </div>
      <span className="text-[11px] tabular-nums text-neutral-400 w-7 text-right">
        {Math.round(value)}%
      </span>
    </div>
  );
}

function EnhancedClaimRow({ claim }: { claim: Claim }) {
  const sentimentPct = claim.sentiment_pct != null ? claim.sentiment_pct * 100 : null;
  const confidenceScore = claim.confidence_score ?? null;
  const mentionsPct = Math.min((claim.mentions ?? 0) / 50 * 100, 100);
  const sentimentTone: "pos" | "neg" | "neu" =
    claim.sentiment === "positive" ? "pos" : claim.sentiment === "negative" ? "neg" : "neu";

  return (
    <div className="px-6 py-4 transition-colors hover:bg-[#161616]">
      <div className="flex items-start gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-medium text-white/85 line-clamp-2 leading-relaxed">
            {claim.claim_text}
          </p>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <Badge tone={getSentimentBadgeTone(claim.sentiment)}>
              {getSentimentLabel(claim.sentiment)}
            </Badge>
            <Badge tone={confidenceScore == null ? "neu" : confidenceScore >= 0.7 ? "pos" : confidenceScore >= 0.4 ? "neu" : "neg"}>
              {confidenceScore == null ? "Unknown" : confidenceScore >= 0.7 ? "High Confidence" : confidenceScore >= 0.4 ? "Med Confidence" : "Low Confidence"}
            </Badge>
            {claim.mentions !== undefined && claim.mentions > 0 && (
              <span className="text-[11px] text-neutral-500">
                {claim.mentions} mention{claim.mentions !== 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>
        <div className="shrink-0 flex flex-col gap-2 pt-0.5">
          <div className="flex items-center gap-3">
            <span className="text-[10px] uppercase tracking-widest text-neutral-600 font-semibold w-16 text-right">Sentiment</span>
            <MiniBar value={sentimentPct ?? 0} tone={sentimentTone} />
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] uppercase tracking-widest text-neutral-600 font-semibold w-16 text-right">Confidence</span>
            <MiniBar value={confidenceScore != null ? confidenceScore * 100 : 0} tone="conf" />
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] uppercase tracking-widest text-neutral-600 font-semibold w-16 text-right">Mentions</span>
            <MiniBar value={mentionsPct} tone="teal" />
          </div>
        </div>
      </div>
    </div>
  );
}

function MentionsToggle({ dir, onChange }: { dir: SortDir; onChange: (d: SortDir) => void }) {
  return (
    <div className="flex items-center gap-1 rounded-md bg-white/5 ring-1 ring-inset ring-white/8 p-0.5">
      <button
        onClick={() => onChange("desc")}
        className={[
          "flex items-center gap-1.5 rounded px-2.5 py-1 text-[11px] font-medium transition-all duration-150",
          dir === "desc"
            ? "bg-teal-500/20 text-teal-300 ring-1 ring-inset ring-teal-500/30"
            : "text-neutral-500 hover:text-neutral-300",
        ].join(" ")}
      >
        <ArrowUpDown className="h-2.5 w-2.5" />
        Most
      </button>
      <button
        onClick={() => onChange("asc")}
        className={[
          "flex items-center gap-1.5 rounded px-2.5 py-1 text-[11px] font-medium transition-all duration-150",
          dir === "asc"
            ? "bg-teal-500/20 text-teal-300 ring-1 ring-inset ring-teal-500/30"
            : "text-neutral-500 hover:text-neutral-300",
        ].join(" ")}
      >
        <ArrowUpDown className="h-2.5 w-2.5" />
        Least
      </button>
    </div>
  );
}

/* ================================================================
   PAGE
================================================================ */

export default function TrendsPage() {
  const [trends, setTrends] = useState<Trend[]>([]);
  const [narratives, setNarratives] = useState<Narrative[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [trendsError, setTrendsError] = useState(false);
  const [narrativesError, setNarrativesError] = useState(false);
  const [claimsError, setClaimsError] = useState(false);
  const [activeCategory, setActiveCategory] = useState<Category>("All");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  useEffect(() => {
    async function fetchData() {
      const [trendsRes, narrativesRes, claimsRes] = await Promise.allSettled([
        getTrends(),
        getNarratives(),
        getDashboardClaims(8),
      ]);

      if (trendsRes.status === "fulfilled") {
        setTrends(trendsRes.value.trends || []);
      } else {
        console.error("[Trends] Failed to fetch trends:", trendsRes.reason);
        setTrendsError(true);
      }

      if (narrativesRes.status === "fulfilled") {
        setNarratives(narrativesRes.value.narratives || []);
      } else {
        console.error("[Trends] Failed to fetch narratives:", narrativesRes.reason);
        setNarrativesError(true);
      }

      if (claimsRes.status === "fulfilled") {
        setClaims(claimsRes.value.claims || []);
      } else {
        console.error("[Trends] Failed to fetch claims:", claimsRes.reason);
        setClaimsError(true);
      }

      setLoading(false);
    }
    fetchData();
  }, []);

  // Trends table is broken if either trends or narratives failed
  const tableError = trendsError || narrativesError;

  const filteredTrends = sortTrends(
    trends.filter((t) => matchesCategory(getNarrativeCategory(t, narratives), activeCategory)),
    sortDir
  );

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
          <SectionLabel>Analysis</SectionLabel>
          <h1
            className="mt-2 text-[clamp(2rem,4vw,2.8rem)] font-black leading-tight tracking-[-0.02em]"
            style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
          >
            Trends
          </h1>
          <p className="mt-2 text-sm text-neutral-500">
            Discover trending topics narratives, and claims across European soccer leagues
          </p>
        </div>

        {/* ── Accent line ── */}
        <div className="mb-6 h-px w-full bg-linear-to-r from-transparent via-teal-500/30 to-transparent" />

        {/* ── Top charts ── */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader
              title="Content Volume by League"
              subtitle="Videos analyzed per league this month"
            />
            <div className="px-6 pb-6 pt-4">
              <BarChart />
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Topic Frequency"
              subtitle="Most discussed topics over the last 6 weeks"
              legendItems={[
                { color: "bg-emerald-400", label: "Transfers" },
                { color: "bg-red-400",     label: "Injuries" },
                { color: "bg-sky-400",     label: "Tactics" },
                { color: "bg-amber-400",   label: "Controversy" },
              ]}
            />
            <div className="px-6 pb-6 pt-4">
              <LineChart />
            </div>
          </Card>
        </div>

        {/* ── Claims ── */}
        <div className="mt-6">
          <Card>
            <CardHeader
              title="Emerging Claims"
              subtitle="Trending claims with sentiment, confidence & mention metrics"
            />
            <div className="flex items-center justify-between border-b border-white/6 px-6 py-2.5">
              <span className="text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Claim</span>
              <span className="text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Metrics</span>
            </div>
            <div className="divide-y divide-white/4">
              {loading ? (
                <ClaimSkeleton />
              ) : claimsError ? (
                <EmptyState message="Failed to load claims" />
              ) : claims.length === 0 ? (
                <EmptyState message="No claims available" />
              ) : (
                claims.map((claim) => (
                  <EnhancedClaimRow key={claim.id} claim={claim} />
                ))
              )}
            </div>
          </Card>
        </div>

        {/* ── Narrative Trends table ── */}
        <div className="mt-6">
          <Card>
            <CardHeader
              title="Headline Narratives"
              subtitle="Leading stories across YouTube soccer channels, organized by topic"
            />

            {/* Category tabs + sort toggle */}
            <div className="flex items-center justify-between border-b border-white/6 px-6 pb-0 pt-3">
              <div className="flex gap-1 overflow-x-auto scrollbar-none">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setActiveCategory(cat)}
                    className={[
                      "relative shrink-0 rounded-t-md px-3.5 py-2 text-[12px] font-medium transition-colors duration-150",
                      activeCategory === cat
                        ? "text-white"
                        : `text-neutral-500 ${CATEGORY_COLORS[cat] ?? "hover:text-neutral-300"}`,
                    ].join(" ")}
                  >
                    {activeCategory === cat && (
                      <span className="absolute inset-0 rounded-t-md bg-white/5 ring-1 ring-inset ring-white/[0.07]" />
                    )}
                    {activeCategory === cat && (
                      <span className={`absolute bottom-0 left-1/2 h-px w-5 -translate-x-1/2 rounded-full ${
                        cat === "Transfers"   ? "bg-emerald-400" :
                        cat === "Injuries"    ? "bg-red-400"     :
                        cat === "Tactics"     ? "bg-sky-400"     :
                        cat === "Controversy" ? "bg-amber-400"   :
                        "bg-teal-400"
                      }`} />
                    )}
                    <span className="relative">{cat}</span>
                  </button>
                ))}
              </div>

              <div className="pb-3 pl-4 shrink-0 flex items-center gap-2">
                <span className="text-[10px] uppercase tracking-widest text-neutral-600 font-semibold hidden sm:block">
                  Mentions
                </span>
                <MentionsToggle dir={sortDir} onChange={setSortDir} />
              </div>
            </div>

            {/* Table column headers */}
            <div className="grid grid-cols-12 gap-4 border-b border-white/4 px-6 py-2.5">
              <div className="col-span-5 text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Topic</div>
              <div className="col-span-3 text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Trend Score</div>
              <div className="col-span-1 text-right text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Mentions</div>
              <div className="col-span-1 text-right text-[11px] font-semibold uppercase tracking-widest text-neutral-600">Change</div>
              <div className="col-span-2 text-right text-[11px] font-semibold uppercase tracking-widest text-neutral-600">League</div>
            </div>

            <div className="divide-y divide-white/4">
              {loading ? (
                <TableSkeleton />
              ) : tableError ? (
                <EmptyState message="Failed to load trends" />
              ) : filteredTrends.length === 0 ? (
                <EmptyState message={activeCategory === "All" ? "No trends available" : `No ${activeCategory} trends found`} />
              ) : (
                filteredTrends.map((trend) => (
                  <TopicRow
                    key={trend.id}
                    hot={trend.trending_direction === "up" && trend.score >= 0.75}
                    topic={
                      narratives.find((n) => n.id === trend.narrative_id)?.title ||
                      trend.league ||
                      "General Topic"
                    }
                    mentions={trend.mention_count.toString()}
                    change={formatChange(trend.trending_direction, trend.mention_count)}
                    changeDir={getChangeDir(trend.trending_direction)}
                    leagues={getTopicLeague(trend)}
                    score={trend.score}
                  />
                ))
              )}
            </div>

            {!loading && !tableError && filteredTrends.length > 0 && (
              <div className="border-t border-white/4 px-6 py-3">
                <span className="text-[11px] text-neutral-600">
                  Showing {filteredTrends.length} of {trends.length} topics
                  {activeCategory !== "All" && ` · filtered by ${activeCategory}`}
                </span>
              </div>
            )}
          </Card>
        </div>

      </div>
    </div>
  );
}
