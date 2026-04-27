import { useState, useRef, useEffect } from "react";
import Badge from "../components/badge";
import { Flame, TrendingUp, TrendingDown, Minus } from "lucide-react";

const VALID_LEAGUES = [
  "Premier League",
  "Champions League",
  "La Liga",
  "Bundesliga",
  "Serie A",
  "Ligue 1",
];

function ScoreBar({ score }: { score: number }) {
  // score is 0–1; normalise to 0–100
  const pct = Math.min(Math.max(score, 0), 1) * 100;

  // Colour matches site convention: teal = high, amber = mid, red = low
  const barColor =
    pct >= 65
      ? "bg-emerald-400"
      : pct >= 40
      ? "bg-amber-400"
      : "bg-red-400";

  return (
    <div className="flex items-center gap-2">
      <div className="h-1 w-30 rounded-full bg-white/8 overflow-hidden">
        <div
          className={`h-full rounded-full ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[11px] tabular-nums text-neutral-400 w-7 text-right">
        {Math.round(pct)}%
      </span>
    </div>
  );
}

export default function TopicRow({
  hot,
  topic,
  description,
  mentions,
  change,
  changeDir,
  leagues,
  score = 0,
}: {
  hot?: boolean;
  topic: string;
  description?: string | null;
  mentions: string;
  change: string;
  changeDir: "up" | "down" | "flat";
  leagues: string[];
  score?: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const [isClamped, setIsClamped] = useState(false);
  const descRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = descRef.current;
    if (el) setIsClamped(el.scrollHeight > el.clientHeight);
  }, [description]);

  const changeColor =
    changeDir === "up"
      ? "text-emerald-400"
      : changeDir === "down"
      ? "text-red-400"
      : "text-neutral-500";

  const ChangeIcon =
    changeDir === "up" ? TrendingUp : changeDir === "down" ? TrendingDown : Minus;

  return (
    <div className="grid grid-cols-12 gap-4 px-6 py-4 transition-colors hover:bg-[#161616] group">
      {/* Topic */}
      <div className="col-span-6 flex items-start gap-3 min-w-0">
        {hot && (
          <div className="pt-0.5">
            <Flame className="h-3.5 w-3.5 shrink-0 text-orange-400 group-hover:animate-pulse" />
          </div>
        )}
        <div className="min-w-0">
          <div className="truncate text-[13px] font-medium text-white/85">{topic}</div>
          {description ? (
            <>
              <div ref={descRef} className={`mt-1 text-[11px] leading-relaxed text-neutral-500 ${expanded ? "" : "line-clamp-2"}`}>
                {description}
              </div>
              {(isClamped || expanded) && (
                <button
                  onClick={() => setExpanded((v) => !v)}
                  className="text-[11px] text-neutral-500 hover:text-neutral-400 transition-colors duration-150 -mt-1"
                >
                  {expanded ? "See less" : "See more"}
                </button>
              )}
            </>
          ) : null}
        </div>
      </div>

      {/* Trend Score */}
      <div className="col-span-2 flex items-center justify-end">
        <ScoreBar score={score} />
      </div>

      {/* Mentions */}
      <div className="col-span-1 flex items-center justify-end">
        <span className="tabular-nums text-[13px] text-neutral-400">{mentions}</span>
      </div>

      {/* Change */}
      <div className={`col-span-1 flex items-center justify-end gap-1.5 ${changeColor}`}>
        <ChangeIcon className="h-3 w-3 shrink-0" />
        <span className="tabular-nums text-[13px]">{change}</span>
      </div>

      {/* Leagues */}
      <div className="col-span-2 flex items-center justify-end gap-1 flex-wrap">
        {leagues
          .filter((l) => VALID_LEAGUES.includes(l))
          .slice(0, 2)
          .map((l) => (
            <Badge key={l} tone="neutral">{l}</Badge>
          ))}
      </div>
    </div>
  );
}