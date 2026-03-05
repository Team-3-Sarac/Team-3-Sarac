import Pill from "../components/pill";
import { Flame, TrendingUp, TrendingDown } from "lucide-react";

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
  const changeCls =
    changeDir === "up"
      ? "text-emerald-400"
      : changeDir === "down"
      ? "text-red-400"
      : "text-neutral-500";

  const ChangeIcon =
    changeDir === "up" ? TrendingUp : changeDir === "down" ? TrendingDown : null;

  return (
    <div className="grid grid-cols-12 items-center gap-4 px-5 py-4">
      <div className="col-span-6 flex items-center gap-3 min-w-0">
        {hot ? <Flame className="h-4 w-4 text-amber-400" /> : <span className="h-4 w-4" />}
        <div className="truncate text-sm font-medium">{topic}</div>
      </div>

      <div className="col-span-2 text-right text-sm font-semibold">{mentions}</div>

      <div className={`col-span-2 text-right text-sm ${changeCls}`}>
        <span className="inline-flex items-center justify-end gap-1">
          {ChangeIcon ? <ChangeIcon className="h-4 w-4" /> : null}
          {change}
        </span>
      </div>

      <div className="col-span-2 flex justify-end gap-2">
        {leagues.map((l) => (
          <Pill key={l}>{l}</Pill>
        ))}
      </div>
    </div>
  );
}