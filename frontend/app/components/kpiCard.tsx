import {
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";

export default function KpiCard({
  title,
  value,
  sub,
  trend,
  icon,
}: {
  title: string;
  value: string;
  sub: string;
  trend: "up" | "down" | "flat";
  icon: React.ReactNode;
}) {
  const TrendIcon =
    trend === "up" ? ArrowUpRight : trend === "down" ? ArrowDownRight : null;

  const trendColor =
    trend === "up"
      ? "text-emerald-400"
      : trend === "down"
      ? "text-red-400"
      : "text-neutral-400";

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-950/40 px-5 py-4 shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
      <div className="flex items-center justify-between">
        <div className="text-xs text-neutral-400">{title}</div>
        {icon}
      </div>
      <div className="mt-2 text-3xl font-semibold tracking-tight">{value}</div>
      <div className={`mt-1 flex items-center gap-1 text-xs ${trendColor}`}>
        {TrendIcon ? <TrendIcon className="h-3.5 w-3.5" /> : null}
        <span>{sub}</span>
      </div>
    </div>
  );
}