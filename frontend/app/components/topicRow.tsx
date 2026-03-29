import Pill from "../components/pill";
import Badge from "../components/badge";
import { Flame, TrendingUp, TrendingDown, Minus } from "lucide-react";

export default function TopicRow({
  hot,
  topic,
  mentions,
  change,
  changeDir,
  leagues,
}: {
  hot?: boolean;
  topic: string;
  mentions: string;
  change: string;
  changeDir: "up" | "down" | "flat";
  leagues: string[];
}) {
  const changeColor =
    changeDir === "up"
      ? "text-emerald-400"
      : changeDir === "down"
      ? "text-red-400"
      : "text-neutral-500";

  const ChangeIcon =
    changeDir === "up" ? TrendingUp : changeDir === "down" ? TrendingDown : Minus;

  return (
    <div className="grid grid-cols-12 gap-4 px-6 py-4 transition-colors hover:bg-[#161616]">
      {/* Topic */}
      <div className="col-span-6 flex items-center gap-3 min-w-0">
        {hot && (
          <Flame className="h-3.5 w-3.5 shrink-0 text-orange-400" />
        )}
        {!hot && <span className="h-3.5 w-3.5 shrink-0" />}
        <span className="truncate text-[13px] font-medium text-white/85">{topic}</span>
      </div>

      {/* Mentions */}
      <div className="col-span-2 flex items-center justify-end">
        <span className="tabular-nums text-[13px] text-neutral-400">{mentions}</span>
      </div>

      {/* Change */}
      <div className={`col-span-2 flex items-center justify-end gap-1.5 ${changeColor}`}>
        <ChangeIcon className="h-3 w-3 shrink-0" />
        <span className="tabular-nums text-[13px]">{change}</span>
      </div>

      {/* Leagues */}
      <div className="col-span-2 flex items-center justify-end gap-1 flex-wrap">
        {leagues.slice(0, 2).map((l) => (
          <Badge key={l} tone="neutral">{l}</Badge>
        ))}
      </div>
    </div>
  );
}